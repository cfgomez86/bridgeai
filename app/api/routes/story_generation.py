import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.database.session import get_db
from app.repositories.impact_analysis_repository import ImpactAnalysisRepository
from app.repositories.requirement_repository import RequirementRepository
from app.repositories.user_story_repository import UserStoryRepository
from app.services.ai_story_generator import AIStoryGenerator
from app.services.story_ai_provider import get_story_ai_provider
from app.services.story_generation_service import StoryGenerationService
from app.services.story_points_calculator import StoryPointsCalculator

logger = get_logger(__name__)

router = APIRouter(tags=["story-generation"])


class StoryGenerationRequest(BaseModel):
    requirement_id: str
    impact_analysis_id: str
    project_id: str


class StoryGenerationResponse(BaseModel):
    story_id: str
    title: str
    story_points: int
    risk_level: str
    generation_time_seconds: float
    request_id: str


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
        settings=settings,
    )


@router.post("/generate-story", response_model=StoryGenerationResponse)
def generate_story(
    body: StoryGenerationRequest,
    request: Request,
    service: StoryGenerationService = Depends(get_story_service),
) -> StoryGenerationResponse:
    request_id = str(getattr(request.state, "request_id", uuid.uuid4()))
    logger.info(
        "POST /generate-story request_id=%s requirement_id=%s analysis_id=%s",
        request_id, body.requirement_id, body.impact_analysis_id,
    )
    try:
        result = service.generate(body.requirement_id, body.impact_analysis_id, body.project_id)
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
        title=result.title,
        story_points=result.story_points,
        risk_level=result.risk_level,
        generation_time_seconds=result.generation_time_seconds,
        request_id=request_id,
    )
