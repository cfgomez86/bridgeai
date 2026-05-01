import asyncio
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from app.api.dependencies import get_current_user
from app.core.context import get_user_id
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
from app.core.context import get_tenant_id
from app.services.ai_story_generator import AIStoryGenerator
from app.services.dependency_analyzer import DependencyAnalyzer
from app.services.ai_story_generator import TransientGenerationError
from app.services.entity_existence_checker import (
    EntityExistenceChecker,
    EntityNotFoundError,
)
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
    force: bool = False
    # Sólo aplica cuando force=true. Distingue dos motivos del override:
    #   - "intentional_new": el usuario sabe que la entidad no existe y la
    #     está creando deliberadamente (no contamina métricas forced).
    #   - "ambiguous": el usuario fuerza pese al aviso de que la entidad
    #     no existe (cae en el bucket forced).
    force_reason: Optional[str] = None


class StoryGenerationResponse(BaseModel):
    story_id: str
    source_connection_id: str
    title: str
    story_points: int
    risk_level: str
    generation_time_seconds: float
    request_id: str
    entity_not_found: bool = False
    generator_model: Optional[str] = None
    generator_calls: int = 0


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
    generator_model: Optional[str] = None
    generator_calls: int = 0


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
    entity_not_found: bool = False


class SystemQualityResponse(BaseModel):
    status: str
    data: Optional[dict] = None


class QualityBucket(BaseModel):
    avg_overall: Optional[float] = None
    count: int = 0
    avg_dispersion: Optional[float] = None


class LiveQualityResponse(BaseModel):
    """Real-time judge metrics partitioned by `user_stories.entity_not_found`.

    `organic` covers stories whose requirement matched the codebase; `forced`
    covers stories generated under degraded inputs (the judge applies hard
    score caps in this case by design — see `story_quality_judge.py`). Reading
    them separately keeps degraded-input runs from polluting the baseline.
    """

    window_days: int
    organic: QualityBucket
    forced: QualityBucket
    all: QualityBucket


def get_story_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> StoryGenerationService:
    code_file_repo = CodeFileRepository(db)
    return StoryGenerationService(
        ai_generator=AIStoryGenerator(get_story_ai_provider(settings), settings),
        requirement_repo=RequirementRepository(db),
        impact_repo=ImpactAnalysisRepository(db),
        story_repo=UserStoryRepository(db),
        points_calculator=StoryPointsCalculator(),
        code_file_repo=code_file_repo,
        settings=settings,
        entity_checker=EntityExistenceChecker(
            code_file_repo=code_file_repo,
            analyzer=DependencyAnalyzer(get_tenant_id()),
        ),
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
        generator_model=getattr(story, "generator_model", None),
        generator_calls=int(getattr(story, "generator_calls", 0) or 0),
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
        result, entity_not_found = await asyncio.to_thread(
            service.generate,
            body.requirement_id,
            body.impact_analysis_id,
            body.project_id,
            body.source_connection_id,
            body.language,
            body.force,
            body.force_reason,
        )
    except EntityNotFoundError as exc:
        logger.info(
            "POST /generate-story entity not found request_id=%s entity=%s suggestions=%s",
            request_id, exc.entity, exc.suggestions,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "ENTITY_NOT_FOUND",
                "entity": exc.entity,
                "message": str(exc),
                "suggestions": exc.suggestions,
                "hint": "Envía force=true para generar la historia de creación, o usa una de las sugerencias.",
            },
        )
    except TransientGenerationError as exc:
        logger.warning(
            "POST /generate-story upstream timeout request_id=%s attempts=%d last=%s",
            request_id, exc.attempts, exc.last_error,
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=(
                "El proveedor de IA no respondió a tiempo tras varios intentos. "
                "Probá de nuevo en unos segundos."
            ),
        )
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    except Exception as exc:
        logger.exception("POST /generate-story failed request_id=%s", request_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Story generation failed due to an internal error.",
        )
    logger.info(
        "POST /generate-story completed request_id=%s story_id=%s points=%d duration=%.3fs entity_not_found=%s",
        request_id, result.story_id, result.story_points, result.generation_time_seconds, entity_not_found,
    )
    return StoryGenerationResponse(
        story_id=result.story_id,
        source_connection_id=body.source_connection_id,
        title=result.title,
        story_points=result.story_points,
        risk_level=result.risk_level,
        generation_time_seconds=result.generation_time_seconds,
        request_id=request_id,
        entity_not_found=entity_not_found,
        generator_model=result.generator_model,
        generator_calls=result.generator_calls,
    )


@router.get("/stories/{story_id}", response_model=StoryDetailResponse)
async def get_story(
    story_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
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
    user_id = get_user_id()
    record = StoryFeedbackRepository(db).upsert(story_id, user_id, body.rating, body.comment)
    return _feedback_record_to_response(record)


@router.get("/stories/{story_id}/feedback", response_model=Optional[FeedbackResponse])
async def get_feedback(
    story_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Optional[FeedbackResponse]:
    user_id = get_user_id()
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
        entity_not_found=domain_story.entity_not_found,
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

    requirement = RequirementRepository(db).find_by_id(
        domain_story.requirement_id, story_model.source_connection_id
    )
    requirement_text = requirement.requirement_text if requirement else None
    requirement_intent = requirement.intent if requirement else None

    judge = get_quality_judge(settings)
    try:
        scores = judge.evaluate(
            domain_story,
            requirement_text=requirement_text,
            requirement_intent=requirement_intent,
            entity_not_found=domain_story.entity_not_found,
        )
    except (ValueError, KeyError) as exc:
        # Schema/JSON parsing failures from the judge — modelo devolvió algo
        # que no podemos interpretar (campos faltantes, JSON inválido, truncado).
        # No es un fallo del proveedor: es una respuesta inutilizable.
        logger.warning(
            "Quality judge returned unparseable response for story %s",
            story_id, exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "JUDGE_UNPARSEABLE",
                "message": (
                    "The quality judge returned a response we could not parse. "
                    "Try again, increase AI_JUDGE_MAX_TOKENS, or switch judge provider."
                ),
                "reason": str(exc)[:200],
            },
        )
    except Exception as exc:
        # Genuine upstream failures: timeouts, 5xx, network errors, rate limits
        # not handled by the provider's internal retry.
        logger.error(
            "Quality judge upstream failure for story %s",
            story_id, exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "JUDGE_UPSTREAM_ERROR",
                "message": "Quality evaluation failed due to an upstream provider error.",
                "error_type": type(exc).__name__,
            },
        )

    score_record = StoryQualityRepository(db).upsert(story_id, scores)
    return QualityMetricsResponse(
        story_id=story_id,
        structural=StructuralMetricsResponse(**structural),
        judge=_score_model_to_judge_response(score_record),
        entity_not_found=domain_story.entity_not_found,
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


@router.get("/system/quality/live", response_model=LiveQualityResponse)
async def get_live_system_quality(
    days: int = 30,
    db: Session = Depends(get_db),
) -> LiveQualityResponse:
    window_days = max(1, min(days, 365))
    since = datetime.utcnow() - timedelta(days=window_days)
    summary = StoryQualityRepository(db).summary_since(since)
    return LiveQualityResponse(
        window_days=window_days,
        organic=QualityBucket(**summary["organic"]),
        forced=QualityBucket(**summary["forced"]),
        all=QualityBucket(**summary["all"]),
    )
