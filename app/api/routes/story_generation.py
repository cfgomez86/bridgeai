import asyncio
import json
import uuid
from pathlib import Path
from typing import Optional

from app.core.auth0_auth import get_current_user
from app.core.context import current_user_id
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.database.session import get_db
from app.models.user import User
from app.repositories.code_file_repository import CodeFileRepository
from app.repositories.impact_analysis_repository import ImpactAnalysisRepository
from app.repositories.requirement_repository import RequirementRepository
from app.repositories.source_connection_repository import SourceConnectionRepository
from app.repositories.story_feedback_repository import StoryFeedbackRepository
from app.repositories.story_quality_repository import StoryQualityRepository
from app.repositories.ticket_integration_repository import TicketIntegrationRepository
from app.repositories.user_story_repository import UserStoryRepository
from app.services.ai_story_generator import AIStoryGenerator
from app.services.story_ai_provider import get_story_ai_provider
from app.services.story_generation_service import StoryGenerationService
from app.services.story_points_calculator import StoryPointsCalculator
from app.services.story_quality_judge import get_quality_judge
from app.services.story_quality_metrics import compute_structural_metrics
from app.utils.json_utils import parse_json_field

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)], tags=["story-generation"])


class StoryGenerationRequest(BaseModel):
    requirement_id: str
    impact_analysis_id: str
    project_id: str
    source_connection_id: str
    language: str = "es"


class StoryGenerationResponse(BaseModel):
    story_id: str
    source_connection_id: str
    title: str
    story_points: int
    risk_level: str
    generation_time_seconds: float
    request_id: str


class SubtaskItem(BaseModel):
    title: str
    description: str = ""


class SubtasksResponse(BaseModel):
    frontend: list[SubtaskItem] = []
    backend: list[SubtaskItem] = []
    configuration: list[SubtaskItem] = []


class StoryDetailResponse(BaseModel):
    story_id: str
    source_connection_id: str
    requirement_id: str
    impact_analysis_id: str
    project_id: str
    title: str
    story_description: str
    acceptance_criteria: list[str]
    subtasks: SubtasksResponse
    definition_of_done: list[str]
    risk_notes: list[str]
    story_points: int
    risk_level: str
    generation_time_seconds: float
    created_at: str
    is_locked: bool = False


class StoryUpdateRequest(BaseModel):
    source_connection_id: str
    title: Optional[str] = None
    story_description: Optional[str] = None
    acceptance_criteria: Optional[list[str]] = None
    subtasks: Optional[dict] = None
    definition_of_done: Optional[list[str]] = None
    risk_notes: Optional[list[str]] = None
    story_points: Optional[int] = None
    risk_level: Optional[str] = None


class FeedbackRequest(BaseModel):
    rating: str  # "thumbs_up" | "thumbs_down"
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: str
    story_id: str
    user_id: str
    rating: str
    comment: Optional[str]
    created_at: str
    updated_at: str


class StructuralMetricsResponse(BaseModel):
    schema_valid: bool
    ac_count: int
    risk_notes_count: int
    subtask_count: int
    cited_paths_total: int
    cited_paths_existing: int
    citation_grounding_ratio: float


class JudgeScoresResponse(BaseModel):
    completeness: float
    specificity: float
    feasibility: float
    risk_coverage: float
    language_consistency: float
    overall: float
    justification: Optional[str]
    judge_model: Optional[str]
    evaluated_at: Optional[str]
    dispersion: Optional[float] = None
    samples_used: Optional[int] = None
    evidence: Optional[dict] = None


class QualityMetricsResponse(BaseModel):
    story_id: str
    structural: StructuralMetricsResponse
    judge: Optional[JudgeScoresResponse] = None


class SystemQualityResponse(BaseModel):
    status: str
    data: Optional[dict] = None


def get_story_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> StoryGenerationService:
    return StoryGenerationService(
        ai_generator=AIStoryGenerator(get_story_ai_provider(settings), settings),
        requirement_repo=RequirementRepository(db),
        impact_repo=ImpactAnalysisRepository(db),
        story_repo=UserStoryRepository(db),
        points_calculator=StoryPointsCalculator(),
        code_file_repo=CodeFileRepository(db),
        settings=settings,
    )


def _score_model_to_judge_response(score_model) -> Optional[JudgeScoresResponse]:
    if score_model is None:
        return None
    evidence: Optional[dict] = None
    raw_evidence = getattr(score_model, "evidence", None)
    if raw_evidence:
        try:
            parsed = json.loads(raw_evidence)
            if isinstance(parsed, dict):
                evidence = parsed
        except (ValueError, TypeError):
            evidence = None
    return JudgeScoresResponse(
        completeness=score_model.completeness,
        specificity=score_model.specificity,
        feasibility=score_model.feasibility,
        risk_coverage=score_model.risk_coverage,
        language_consistency=score_model.language_consistency,
        overall=score_model.overall,
        justification=score_model.justification,
        judge_model=score_model.judge_model,
        evaluated_at=score_model.evaluated_at.isoformat() if score_model.evaluated_at else None,
        dispersion=getattr(score_model, "dispersion", None),
        samples_used=getattr(score_model, "samples_used", None),
        evidence=evidence,
    )


def _feedback_record_to_response(record) -> FeedbackResponse:
    return FeedbackResponse(
        id=str(record.id),
        story_id=str(record.story_id),
        user_id=record.user_id,
        rating=record.rating,
        comment=record.comment,
        created_at=record.created_at.isoformat(),
        updated_at=record.updated_at.isoformat(),
    )


def _story_to_detail_response(story, is_locked: bool = False) -> StoryDetailResponse:
    raw_subtasks = json.loads(story.subtasks) if story.subtasks else {}
    return StoryDetailResponse(
        story_id=story.id,
        source_connection_id=story.source_connection_id,
        requirement_id=story.requirement_id,
        impact_analysis_id=story.impact_analysis_id,
        project_id=story.project_id,
        title=story.title,
        story_description=story.story_description,
        acceptance_criteria=parse_json_field(story.acceptance_criteria),
        subtasks=SubtasksResponse(
            frontend=raw_subtasks.get("frontend", []),
            backend=raw_subtasks.get("backend", []),
            configuration=raw_subtasks.get("configuration", []),
        ),
        definition_of_done=parse_json_field(story.definition_of_done),
        risk_notes=parse_json_field(story.risk_notes),
        story_points=story.story_points,
        risk_level=story.risk_level,
        generation_time_seconds=story.generation_time_seconds,
        created_at=story.created_at.isoformat(),
        is_locked=is_locked,
    )


@router.post("/generate-story", response_model=StoryGenerationResponse)
async def generate_story(
    body: StoryGenerationRequest,
    request: Request,
    db: Session = Depends(get_db),
    service: StoryGenerationService = Depends(get_story_service),
) -> StoryGenerationResponse:
    request_id = str(getattr(request.state, "request_id", uuid.uuid4()))
    logger.info(
        "POST /generate-story request_id=%s connection=%s requirement_id=%s analysis_id=%s",
        request_id, body.source_connection_id, body.requirement_id, body.impact_analysis_id,
    )

    conn = SourceConnectionRepository(db).find_by_id(body.source_connection_id)
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source connection {body.source_connection_id!r} not found",
        )

    try:
        result = await asyncio.to_thread(
            service.generate,
            body.requirement_id,
            body.impact_analysis_id,
            body.project_id,
            body.source_connection_id,
            body.language,
        )
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    except Exception as exc:
        logger.error("POST /generate-story failed request_id=%s error=%s", request_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Story generation failed: {exc}",
        )
    logger.info(
        "POST /generate-story completed request_id=%s story_id=%s points=%d duration=%.3fs",
        request_id, result.story_id, result.story_points, result.generation_time_seconds,
    )
    return StoryGenerationResponse(
        story_id=result.story_id,
        source_connection_id=body.source_connection_id,
        title=result.title,
        story_points=result.story_points,
        risk_level=result.risk_level,
        generation_time_seconds=result.generation_time_seconds,
        request_id=request_id,
    )


@router.get("/stories/{story_id}", response_model=StoryDetailResponse)
async def get_story(
    story_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> StoryDetailResponse:
    request_id = str(getattr(request.state, "request_id", uuid.uuid4()))
    logger.info("GET /stories/%s request_id=%s", story_id, request_id)
    story = UserStoryRepository(db).find_by_id(story_id)
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story {story_id!r} not found",
        )
    is_locked = TicketIntegrationRepository(db).exists_for_story(story_id)
    logger.info("GET /stories/%s completed request_id=%s", story_id, request_id)
    return _story_to_detail_response(story, is_locked=is_locked)


@router.patch("/stories/{story_id}", response_model=StoryDetailResponse)
async def update_story(
    story_id: str,
    body: StoryUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> StoryDetailResponse:
    request_id = str(getattr(request.state, "request_id", uuid.uuid4()))
    logger.info("PATCH /stories/%s request_id=%s", story_id, request_id)

    ticket_repo = TicketIntegrationRepository(db)
    if ticket_repo.exists_for_story(story_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Story is locked because a ticket has been created",
        )

    story_repo = UserStoryRepository(db)
    story = story_repo.find_by_id_scoped(story_id, body.source_connection_id)
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story {story_id!r} not found",
        )

    update_fields = {}
    content_fields = {"title", "story_description", "acceptance_criteria", "subtasks",
                      "definition_of_done", "risk_notes"}
    for field in (
        "title", "story_description", "acceptance_criteria", "subtasks",
        "definition_of_done", "risk_notes", "story_points", "risk_level"
    ):
        val = getattr(body, field)
        if val is not None:
            update_fields[field] = val

    if update_fields:
        # Invalidate quality score if content-related fields changed
        if update_fields.keys() & content_fields:
            StoryQualityRepository(db).delete_by_story(story_id)
        story = story_repo.update_story(story_id, body.source_connection_id, **update_fields)
        if story is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Story {story_id!r} not found after update",
            )

    logger.info("PATCH /stories/%s completed request_id=%s", story_id, request_id)
    return _story_to_detail_response(story, is_locked=False)


@router.post("/stories/{story_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    story_id: str,
    body: FeedbackRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> FeedbackResponse:
    if body.rating not in ("thumbs_up", "thumbs_down"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="rating must be 'thumbs_up' or 'thumbs_down'",
        )
    story = UserStoryRepository(db).find_by_id(story_id)
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story {story_id!r} not found",
        )
    user_id = current_user_id.get()
    record = StoryFeedbackRepository(db).upsert(story_id, user_id, body.rating, body.comment)
    return _feedback_record_to_response(record)


@router.get("/stories/{story_id}/feedback", response_model=Optional[FeedbackResponse])
async def get_feedback(
    story_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Optional[FeedbackResponse]:
    user_id = current_user_id.get()
    record = StoryFeedbackRepository(db).find_by_user(story_id, user_id)
    if record is None:
        return None
    return _feedback_record_to_response(record)


def _load_story_or_404(story_id: str, db: Session):
    """Fetch ORM story model and convert to domain object in one round-trip."""
    story_model = UserStoryRepository(db).find_by_id(story_id)
    if story_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story {story_id!r} not found",
        )
    return story_model, UserStoryRepository.to_domain(story_model)


@router.get("/stories/{story_id}/quality", response_model=QualityMetricsResponse)
async def get_quality(
    story_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> QualityMetricsResponse:
    story_model, domain_story = _load_story_or_404(story_id, db)
    structural = compute_structural_metrics(
        domain_story, CodeFileRepository(db), story_model.source_connection_id
    )
    score_model = StoryQualityRepository(db).find_by_story(story_id)
    return QualityMetricsResponse(
        story_id=story_id,
        structural=StructuralMetricsResponse(**structural),
        judge=_score_model_to_judge_response(score_model),
    )


@router.post("/stories/{story_id}/quality/evaluate", response_model=QualityMetricsResponse)
async def evaluate_quality(
    story_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _user: User = Depends(get_current_user),
) -> QualityMetricsResponse:
    story_model, domain_story = _load_story_or_404(story_id, db)
    structural = compute_structural_metrics(
        domain_story, CodeFileRepository(db), story_model.source_connection_id
    )

    judge = get_quality_judge(settings)
    try:
        scores = judge.evaluate(domain_story)
    except Exception as exc:
        logger.error("Quality judge failed for story %s: %s", story_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Quality evaluation failed: {exc}",
        )

    score_record = StoryQualityRepository(db).upsert(story_id, scores)
    return QualityMetricsResponse(
        story_id=story_id,
        structural=StructuralMetricsResponse(**structural),
        judge=_score_model_to_judge_response(score_record),
    )


@router.get("/system/quality", response_model=SystemQualityResponse)
async def get_system_quality(
    settings: Settings = Depends(get_settings),
) -> SystemQualityResponse:
    try:
        data = json.loads(Path(settings.EVAL_REPORT_PATH).read_text(encoding="utf-8"))
        return SystemQualityResponse(status="ok", data=data)
    except (OSError, ValueError) as exc:
        logger.debug("Eval report not available at %s: %s", settings.EVAL_REPORT_PATH, exc)
        return SystemQualityResponse(status="not_evaluated")
