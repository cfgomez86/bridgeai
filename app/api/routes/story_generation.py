import asyncio
import json
import uuid
from app.core.auth0_auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.database.session import get_db
from app.repositories.code_file_repository import CodeFileRepository
from app.repositories.impact_analysis_repository import ImpactAnalysisRepository
from app.repositories.requirement_repository import RequirementRepository
from app.repositories.source_connection_repository import SourceConnectionRepository
from app.repositories.user_story_repository import UserStoryRepository
from app.services.ai_story_generator import AIStoryGenerator
from app.services.story_ai_provider import get_story_ai_provider
from app.services.story_generation_service import StoryGenerationService
from app.services.story_points_calculator import StoryPointsCalculator
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
    logger.info("GET /stories/%s completed request_id=%s", story_id, request_id)
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
    )
