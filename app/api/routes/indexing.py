import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.models.code_file import CodeFile  # noqa: F401 — ensures table is registered
from app.repositories.code_file_repository import CodeFileRepository
from app.services.code_indexing_service import CodeIndexingService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["indexing"])


class IndexRequest(BaseModel):
    force: bool = False


class IndexResponse(BaseModel):
    files_scanned: int
    files_indexed: int
    files_skipped: int
    files_updated: int
    duration_seconds: float
    request_id: str


def get_indexing_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CodeIndexingService:
    repo = CodeFileRepository(db)
    return CodeIndexingService(repo, settings.PROJECT_ROOT)


@router.post("/index", response_model=IndexResponse)
async def index_repository(
    body: IndexRequest,
    request: Request,
    service: CodeIndexingService = Depends(get_indexing_service),
) -> IndexResponse:
    request_id = str(uuid.uuid4())

    logger.info(
        "POST /index started request_id=%s force=%s", request_id, body.force
    )

    try:
        result = service.index_repository(force=body.force)
    except Exception as exc:
        logger.error(
            "POST /index failed request_id=%s error=%s", request_id, exc
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Indexing failed: {exc}",
        ) from exc

    logger.info(
        "POST /index completed request_id=%s duration=%.2fs files_indexed=%d",
        request_id,
        result.duration_seconds,
        result.files_indexed,
    )

    return IndexResponse(
        files_scanned=result.files_scanned,
        files_indexed=result.files_indexed,
        files_skipped=result.files_skipped,
        files_updated=result.files_updated,
        duration_seconds=result.duration_seconds,
        request_id=request_id,
    )
