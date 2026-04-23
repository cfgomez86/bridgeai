import asyncio
import uuid
from app.core.auth0_auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.database.session import get_db
from app.repositories.requirement_repository import RequirementRepository
from app.repositories.source_connection_repository import SourceConnectionRepository
from app.services.ai_provider import get_ai_provider
from app.services.ai_requirement_parser import AIRequirementParser
from app.services.requirement_understanding_service import RequirementUnderstandingService

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)], tags=["requirement-understanding"])


class UnderstandRequest(BaseModel):
    requirement: str
    project_id: str
    source_connection_id: str


class UnderstandResponse(BaseModel):
    requirement_id: str
    source_connection_id: str
    intent: str
    feature_type: str
    estimated_complexity: str
    keywords: list[str]
    processing_time_seconds: float
    request_id: str


def get_understanding_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RequirementUnderstandingService:
    repo = RequirementRepository(db)
    parser = AIRequirementParser(get_ai_provider(settings))
    return RequirementUnderstandingService(parser, repo, settings)


@router.post("/understand-requirement", response_model=UnderstandResponse)
async def understand_requirement(
    body: UnderstandRequest,
    request: Request,
    db: Session = Depends(get_db),
    service: RequirementUnderstandingService = Depends(get_understanding_service),
) -> UnderstandResponse:
    request_id = str(getattr(request.state, "request_id", uuid.uuid4()))
    logger.info(
        "POST /understand-requirement request_id=%s connection=%s requirement=%.100s",
        request_id, body.source_connection_id, body.requirement,
    )

    # Valida que la conexión pertenezca al tenant actual
    conn = SourceConnectionRepository(db).find_by_id(body.source_connection_id)
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source connection {body.source_connection_id!r} not found",
        )

    try:
        result = await asyncio.to_thread(
            service.understand, body.requirement, body.project_id, body.source_connection_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error("POST /understand-requirement failed request_id=%s error=%s", request_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Understanding failed: {exc}",
        )
    logger.info(
        "POST /understand-requirement completed request_id=%s id=%s complexity=%s duration=%.3fs",
        request_id,
        result.requirement_id,
        result.estimated_complexity,
        result.processing_time_seconds,
    )
    return UnderstandResponse(
        requirement_id=result.requirement_id,
        source_connection_id=body.source_connection_id,
        intent=result.intent,
        feature_type=result.feature_type,
        estimated_complexity=result.estimated_complexity,
        keywords=result.keywords,
        processing_time_seconds=result.processing_time_seconds,
        request_id=request_id,
    )
