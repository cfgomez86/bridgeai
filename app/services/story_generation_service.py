import json
import os
import uuid
from datetime import datetime, timezone

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.domain.user_story import UserStory
from app.models.user_story import UserStory as UserStoryModel
from app.repositories.code_file_repository import CodeFileRepository
from app.repositories.impact_analysis_repository import ImpactAnalysisRepository
from app.repositories.requirement_repository import RequirementRepository
from app.repositories.user_story_repository import UserStoryRepository
from app.services.ai_story_generator import AIStoryGenerator
from app.services.entity_existence_checker import (
    EntityExistenceChecker,
    EntityNotFoundError,
)
from app.services.story_points_calculator import StoryPointsCalculator

_WHITELIST_CAP = 150
_VALID_FORCE_REASONS = {"intentional_new", "ambiguous"}


class StoryGenerationService:
    def __init__(
        self,
        ai_generator: AIStoryGenerator,
        requirement_repo: RequirementRepository,
        impact_repo: ImpactAnalysisRepository,
        story_repo: UserStoryRepository,
        points_calculator: StoryPointsCalculator,
        code_file_repo: CodeFileRepository,
        settings: Settings = None,
        entity_checker: EntityExistenceChecker | None = None,
    ) -> None:
        self._generator = ai_generator
        self._requirement_repo = requirement_repo
        self._impact_repo = impact_repo
        self._story_repo = story_repo
        self._points_calculator = points_calculator
        self._code_file_repo = code_file_repo
        self._settings = settings or get_settings()
        self._entity_checker = entity_checker
        self._logger = get_logger(__name__)

    def generate(
        self,
        requirement_id: str,
        analysis_id: str,
        project_id: str,
        source_connection_id: str,
        language: str = "es",
        force: bool = False,
        force_reason: str | None = None,
    ) -> tuple[UserStory, bool]:
        if not source_connection_id:
            raise ValueError("source_connection_id is required")
        if force_reason is not None and force_reason not in _VALID_FORCE_REASONS:
            raise ValueError(
                f"force_reason must be one of {_VALID_FORCE_REASONS} or omitted"
            )

        cached = self._story_repo.find_by_requirement_and_analysis(
            requirement_id, analysis_id, source_connection_id, language
        )
        if cached:
            self._logger.info(
                "Cache hit for requirement_id=%s analysis_id=%s connection=%s",
                requirement_id, analysis_id, source_connection_id,
            )
            return self._to_domain(cached), False

        requirement = self._requirement_repo.find_by_id(requirement_id, source_connection_id)
        if not requirement:
            # No existe o pertenece a otra conexión: bloqueamos cross-repo aunque
            # el cliente haya combinado IDs de distintos repos.
            raise ValueError(
                f"Requirement {requirement_id} not found for connection {source_connection_id}"
            )

        analysis = self._impact_repo.find_by_id(analysis_id, source_connection_id)
        if not analysis:
            raise ValueError(
                f"ImpactAnalysis {analysis_id} not found for connection {source_connection_id}"
            )

        # Si la entidad principal no existe en el codebase indexado, hay tres
        # rutas: (1) sin force, levantar 422 para que el frontend muestre el modal;
        # (2) force con reason='intentional_new', proceder y NO marcar
        # entity_not_found (es una entidad nueva legítima que el usuario está
        # creando deliberadamente — no debería contaminar el bucket "forced" del
        # dashboard ni mostrar banner de degradado); (3) force con
        # reason='ambiguous' o sin reason, proceder marcando entity_not_found=True
        # para que el judge aplique más rigor y la HU quede etiquetada como
        # forzada en métricas.
        entity_not_found = False
        if (
            self._entity_checker is not None
            and self._settings.ENTITY_VALIDATION_MODE != "off"
        ):
            check = self._entity_checker.check(requirement.entity, source_connection_id)
            if not check.found:
                if not force:
                    raise EntityNotFoundError(requirement.entity, check.suggestions)
                entity_not_found = force_reason != "intentional_new"
                self._logger.info(
                    "Entity '%s' not found, proceeding (force=True, reason=%s, entity_not_found=%s)",
                    requirement.entity, force_reason, entity_not_found,
                )

        impacted_file_paths = self._impact_repo.find_file_paths(analysis_id, source_connection_id)
        all_paths = self._code_file_repo.get_all_paths(source_connection_id)
        available_file_paths = self._build_whitelist(
            all_paths, impacted_file_paths, _WHITELIST_CAP
        )

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
            "impacted_file_paths": impacted_file_paths,
            "available_file_paths": available_file_paths,
            "language": language,
            "entity": requirement.entity,
            "entity_not_found": entity_not_found,
        }

        start = datetime.now(timezone.utc)
        parsed = self._generator.generate(context)
        generation_time = (datetime.now(timezone.utc) - start).total_seconds()
        generator_calls = self._generator.last_call_count

        story_points = self._points_calculator.calculate(
            requirement.estimated_complexity,
            analysis.files_impacted,
            analysis.risk_level,
        )

        story_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)
        generator_model = self._generator.model_name

        self._story_repo.save({
            "id": story_id,
            "requirement_id": requirement_id,
            "impact_analysis_id": analysis_id,
            "project_id": project_id,
            "language": language,
            "title": parsed["title"],
            "story_description": parsed["story_description"],
            "acceptance_criteria": json.dumps(parsed["acceptance_criteria"]),
            "subtasks": json.dumps(parsed["subtasks"]),
            "definition_of_done": json.dumps(parsed["definition_of_done"]),
            "risk_notes": json.dumps(parsed["risk_notes"]),
            "story_points": story_points,
            "risk_level": analysis.risk_level,
            "generation_time_seconds": generation_time,
            "entity_not_found": entity_not_found,
            "was_forced": force,
            "force_reason": force_reason if force else None,
            "generator_model": generator_model,
            "generator_calls": generator_calls,
            "created_at": created_at,
        }, source_connection_id)
        self._logger.info(
            "Story generated id=%s connection=%s points=%d time=%.3fs",
            story_id, source_connection_id, story_points, generation_time,
        )

        return (
            UserStory(
                story_id=story_id,
                requirement_id=requirement_id,
                impact_analysis_id=analysis_id,
                project_id=project_id,
                title=parsed["title"],
                story_description=parsed["story_description"],
                acceptance_criteria=parsed["acceptance_criteria"],
                subtasks=parsed["subtasks"],
                definition_of_done=parsed["definition_of_done"],
                risk_notes=parsed["risk_notes"],
                story_points=story_points,
                risk_level=analysis.risk_level,
                created_at=created_at,
                generation_time_seconds=generation_time,
                entity_not_found=entity_not_found,
                was_forced=force,
                force_reason=force_reason if force else None,
                generator_model=generator_model,
                generator_calls=generator_calls,
            ),
            entity_not_found,
        )

    @staticmethod
    def _build_whitelist(
        all_paths: set[str], impacted: list[str], cap: int
    ) -> list[str]:
        """Prioriza rutas que el AI puede citar: impactadas → mismo módulo → sample."""
        if not all_paths:
            return []
        if len(all_paths) <= cap:
            return sorted(all_paths)

        selected: set[str] = set(p for p in impacted if p in all_paths)
        parent_dirs = {os.path.dirname(p) for p in selected if os.path.dirname(p)}
        for p in sorted(all_paths):
            if len(selected) >= cap:
                break
            parent = os.path.dirname(p)
            if any(parent == d or parent.startswith(d + "/") for d in parent_dirs):
                selected.add(p)
        for p in sorted(all_paths):
            if len(selected) >= cap:
                break
            selected.add(p)
        return sorted(selected)

    def _to_domain(self, orm: UserStoryModel) -> UserStory:
        return UserStory(
            story_id=orm.id,
            requirement_id=orm.requirement_id,
            impact_analysis_id=orm.impact_analysis_id,
            project_id=orm.project_id,
            title=orm.title,
            story_description=orm.story_description,
            acceptance_criteria=json.loads(orm.acceptance_criteria),
            subtasks=json.loads(orm.subtasks) if orm.subtasks else {"frontend": [], "backend": [], "configuration": []},
            definition_of_done=json.loads(orm.definition_of_done),
            risk_notes=json.loads(orm.risk_notes),
            story_points=orm.story_points,
            risk_level=orm.risk_level,
            created_at=orm.created_at,
            generation_time_seconds=orm.generation_time_seconds,
            entity_not_found=bool(getattr(orm, "entity_not_found", False)),
            was_forced=bool(getattr(orm, "was_forced", False)),
            force_reason=getattr(orm, "force_reason", None),
            generator_model=getattr(orm, "generator_model", None),
            generator_calls=int(getattr(orm, "generator_calls", 0) or 0),
        )
