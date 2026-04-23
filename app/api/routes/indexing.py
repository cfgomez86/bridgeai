import logging
import uuid
from datetime import datetime
from typing import Optional

from app.core.auth0_auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.models.code_file import CodeFile  # noqa: F401 — ensures table is registered
from app.repositories.code_file_repository import CodeFileRepository
from app.repositories.source_connection_repository import SourceConnectionRepository
from app.services.code_indexing_service import CodeIndexingService
from app.services.scm_providers import get_provider

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)], tags=["indexing"])


class IndexRequest(BaseModel):
    force: bool = False


class IndexResponse(BaseModel):
    files_scanned: int
    files_indexed: int
    files_skipped: int
    files_updated: int
    duration_seconds: float
    request_id: str
    source: str = "local"
    repo_full_name: str | None = None


class IndexStatusResponse(BaseModel):
    total_files: int
    last_indexed_at: Optional[datetime] = None


def get_indexing_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CodeIndexingService:
    repo = CodeFileRepository(db)
    return CodeIndexingService(repo, settings.PROJECT_ROOT)


@router.get("/index/status", response_model=IndexStatusResponse)
async def get_index_status(
    db: Session = Depends(get_db),
    service: CodeIndexingService = Depends(get_indexing_service),
) -> IndexStatusResponse:
    active = SourceConnectionRepository(db).get_active()
    source_connection_id = active.id if active else None
    total_files, last_indexed_at = service.get_status(source_connection_id)
    return IndexStatusResponse(total_files=total_files, last_indexed_at=last_indexed_at)


@router.post("/index", response_model=IndexResponse)
async def index_repository(
    body: IndexRequest,
    request: Request,
    db: Session = Depends(get_db),
    service: CodeIndexingService = Depends(get_indexing_service),
) -> IndexResponse:
    request_id = str(uuid.uuid4())
    logger.info("POST /index started request_id=%s force=%s", request_id, body.force)

    source = "local"
    repo_full_name = None

    try:
        conn_repo = SourceConnectionRepository(db)
        active = conn_repo.get_active()

        if active and active.repo_full_name and active.access_token:
            provider = get_provider(active.platform)
            branch = active.default_branch or "main"
            result = service.index_remote(
                provider=provider,
                access_token=active.access_token,
                repo_full_name=active.repo_full_name,
                branch=branch,
                force=body.force,
                source_connection_id=active.id,
            )
            source = "remote"
            repo_full_name = active.repo_full_name
        else:
            # Local fallback: aún así scopeamos por la conexión activa cuando
            # existe, para que el análisis posterior encuentre los archivos.
            result = service.index_repository(
                force=body.force,
                source_connection_id=active.id if active else None,
            )

    except Exception as exc:
        logger.error("POST /index failed request_id=%s error=%s", request_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Indexing failed: {exc}",
        ) from exc

    logger.info(
        "POST /index completed request_id=%s source=%s duration=%.2fs files_indexed=%d",
        request_id, source, result.duration_seconds, result.files_indexed,
    )

    return IndexResponse(
        files_scanned=result.files_scanned,
        files_indexed=result.files_indexed,
        files_skipped=result.files_skipped,
        files_updated=result.files_updated,
        duration_seconds=result.duration_seconds,
        request_id=request_id,
        source=source,
        repo_full_name=repo_full_name,
    )
