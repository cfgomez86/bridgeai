import asyncio
import uuid

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.api.dependencies import get_current_user, get_source_connection_repo, get_understanding_service
from app.core.logging import get_logger
from app.services.requirement_coherence_validator import IncoherentRequirementError
from app.services.requirement_understanding_service import RequirementUnderstandingService

if TYPE_CHECKING:
    from app.repositories.source_connection_repository import SourceConnectionRepository

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
    evaluated_by_model: str | None = None
    coherence_model: str | None = None
    coherence_calls: int = 0
    parser_model: str | None = None
    parser_calls: int = 0


@router.post("/understand-requirement", response_model=UnderstandResponse)
async def understand_requirement(
    body: UnderstandRequest,
    request: Request,
    scm_repo: SourceConnectionRepository = Depends(get_source_connection_repo),
    service: RequirementUnderstandingService = Depends(get_understanding_service),
) -> UnderstandResponse:
    request_id = str(getattr(request.state, "request_id", uuid.uuid4()))
    logger.info(
        "POST /understand-requirement request_id=%s connection=%s requirement=%.100s",
        request_id, body.source_connection_id, body.requirement,
    )

    # Valida que la conexión pertenezca al tenant actual
    conn = scm_repo.find_by_id(body.source_connection_id)
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source connection {body.source_connection_id!r} not found",
        )

    try:
        result = await asyncio.to_thread(
            service.understand, body.requirement, body.project_id, body.source_connection_id
        )
    except IncoherentRequirementError as exc:
        logger.info(
            "POST /understand-requirement rejected by coherence filter request_id=%s codes=%s model=%s",
            request_id, exc.reason_codes, exc.model_used,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INCOHERENT_REQUIREMENT",
                "message": exc.warning,
                "reason_codes": exc.reason_codes,
            },
        )
    except ValueError as exc:
        # Safe: all ValueErrors from RequirementUnderstandingService are fixed developer strings.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error("POST /understand-requirement failed request_id=%s error=%s", request_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Requirement understanding failed due to an internal error.",
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
        evaluated_by_model=service.parser_model_name or None,
        coherence_model=result.coherence_model,
        coherence_calls=result.coherence_calls,
        parser_model=result.parser_model,
        parser_calls=result.parser_calls,
    )
