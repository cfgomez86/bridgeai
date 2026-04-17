import json
import uuid
from datetime import datetime, timezone

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.domain.user_story import UserStory
from app.models.user_story import UserStory as UserStoryModel
from app.repositories.impact_analysis_repository import ImpactAnalysisRepository
from app.repositories.requirement_repository import RequirementRepository
from app.repositories.user_story_repository import UserStoryRepository
from app.services.ai_story_generator import AIStoryGenerator
from app.services.story_points_calculator import StoryPointsCalculator


class StoryGenerationService:
    def __init__(
        self,
        ai_generator: AIStoryGenerator,
        requirement_repo: RequirementRepository,
        impact_repo: ImpactAnalysisRepository,
        story_repo: UserStoryRepository,
        points_calculator: StoryPointsCalculator,
        settings: Settings = None,
    ) -> None:
        self._generator = ai_generator
        self._requirement_repo = requirement_repo
        self._impact_repo = impact_repo
        self._story_repo = story_repo
        self._points_calculator = points_calculator
        self._settings = settings or get_settings()
        self._logger = get_logger(__name__)

    def generate(self, requirement_id: str, analysis_id: str, project_id: str) -> UserStory:
        cached = self._story_repo.find_by_requirement_and_analysis(requirement_id, analysis_id)
        if cached:
            self._logger.info("Cache hit for requirement_id=%s analysis_id=%s", requirement_id, analysis_id)
            return self._to_domain(cached)

        requirement = self._requirement_repo.find_by_id(requirement_id)
        if not requirement:
            raise ValueError(f"Requirement {requirement_id} not found")

        analysis = self._impact_repo.find_by_id(analysis_id)
        if not analysis:
            raise ValueError(f"ImpactAnalysis {analysis_id} not found")

        context = {
            "requirement_text": requirement.requirement_text,
            "intent": requirement.intent,
            "feature_type": requirement.feature_type,
            "business_domain": requirement.business_domain,
            "estimated_complexity": requirement.estimated_complexity,
            "keywords": json.loads(requirement.keywords),
            "files_impacted": analysis.files_impacted,
            "modules_impacted": analysis.modules_impacted,
            "risk_level": analysis.risk_level,
        }

        start = datetime.now(timezone.utc)
        parsed = self._generator.generate(context)
        generation_time = (datetime.now(timezone.utc) - start).total_seconds()

        story_points = self._points_calculator.calculate(
            requirement.estimated_complexity,
            analysis.files_impacted,
            analysis.risk_level,
        )

        story_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)

        orm_story = UserStoryModel(
            id=story_id,
            requirement_id=requirement_id,
            impact_analysis_id=analysis_id,
            project_id=project_id,
            title=parsed["title"],
            story_description=parsed["story_description"],
            acceptance_criteria=json.dumps(parsed["acceptance_criteria"]),
            technical_tasks=json.dumps(parsed["technical_tasks"]),
            definition_of_done=json.dumps(parsed["definition_of_done"]),
            risk_notes=json.dumps(parsed["risk_notes"]),
            story_points=story_points,
            risk_level=analysis.risk_level,
            generation_time_seconds=generation_time,
            created_at=created_at,
        )
        self._story_repo.save(orm_story)
        self._logger.info(
            "Story generated id=%s points=%d time=%.3fs",
            story_id, story_points, generation_time,
        )

        return UserStory(
            story_id=story_id,
            requirement_id=requirement_id,
            impact_analysis_id=analysis_id,
            project_id=project_id,
            title=parsed["title"],
            story_description=parsed["story_description"],
            acceptance_criteria=parsed["acceptance_criteria"],
            technical_tasks=parsed["technical_tasks"],
            definition_of_done=parsed["definition_of_done"],
            risk_notes=parsed["risk_notes"],
            story_points=story_points,
            risk_level=analysis.risk_level,
            created_at=created_at,
            generation_time_seconds=generation_time,
        )

    def _to_domain(self, orm: UserStoryModel) -> UserStory:
        return UserStory(
            story_id=orm.id,
            requirement_id=orm.requirement_id,
            impact_analysis_id=orm.impact_analysis_id,
            project_id=orm.project_id,
            title=orm.title,
            story_description=orm.story_description,
            acceptance_criteria=json.loads(orm.acceptance_criteria),
            technical_tasks=json.loads(orm.technical_tasks),
            definition_of_done=json.loads(orm.definition_of_done),
            risk_notes=json.loads(orm.risk_notes),
            story_points=orm.story_points,
            risk_level=orm.risk_level,
            created_at=orm.created_at,
            generation_time_seconds=orm.generation_time_seconds,
        )
