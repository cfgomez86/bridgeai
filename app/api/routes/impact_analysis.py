import asyncio
import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.models.impact_analysis import ImpactAnalysis, ImpactedFile  # noqa: F401
from app.repositories.code_file_repository import CodeFileRepository
from app.repositories.impact_analysis_repository import ImpactAnalysisRepository
from app.services.dependency_analyzer import DependencyAnalyzer
from app.services.impact_analysis_service import ImpactAnalysisService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["impact-analysis"])


class ImpactAnalysisRequest(BaseModel):
    requirement: str
    project_id: str


class ImpactAnalysisResponse(BaseModel):
    analysis_id: str
    files_impacted: int
    modules_impacted: list[str]
    risk_level: str
    duration_seconds: float
    request_id: str


class ImpactedFileItem(BaseModel):
    file_path: str
    reason: str


class ImpactedFilesPage(BaseModel):
    analysis_id: str
    total: int
    offset: int
    limit: int
    items: list[ImpactedFileItem]


def get_impact_repo(db: Session = Depends(get_db)) -> ImpactAnalysisRepository:
    return ImpactAnalysisRepository(db)


def get_impact_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ImpactAnalysisService:
    code_repo = CodeFileRepository(db)
    impact_repo = ImpactAnalysisRepository(db)
    return ImpactAnalysisService(code_repo, impact_repo, settings.PROJECT_ROOT, DependencyAnalyzer())


@router.post("/impact-analysis", response_model=ImpactAnalysisResponse)
async def analyze_impact(
    body: ImpactAnalysisRequest,
    service: ImpactAnalysisService = Depends(get_impact_service),
) -> ImpactAnalysisResponse:
    request_id: str = str(uuid.uuid4())
    logger.info("POST /impact-analysis started request_id=%s requirement=%r", request_id, body.requirement)
    try:
        result = await asyncio.to_thread(service.analyze, body.requirement, body.project_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error("POST /impact-analysis failed request_id=%s error=%s", request_id, exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analysis failed: {exc}")
    logger.info(
        "POST /impact-analysis completed request_id=%s files=%d risk=%s duration=%.2fs",
        request_id,
        result.files_impacted,
        result.risk_level,
        result.duration_seconds,
    )
    return ImpactAnalysisResponse(
        analysis_id=result.analysis_id,
        files_impacted=result.files_impacted,
        modules_impacted=result.modules_impacted,
        risk_level=result.risk_level,
        duration_seconds=result.duration_seconds,
        request_id=request_id,
    )


@router.get("/impact-analysis/{analysis_id}/files", response_model=ImpactedFilesPage)
async def get_impacted_files(
    analysis_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    repo: ImpactAnalysisRepository = Depends(get_impact_repo),
) -> ImpactedFilesPage:
    analysis = await asyncio.to_thread(repo.find_by_id, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Analysis {analysis_id!r} not found")
    files, total = await asyncio.to_thread(repo.find_files_page, analysis_id, offset, limit)
    return ImpactedFilesPage(
        analysis_id=analysis_id,
        total=total,
        offset=offset,
        limit=limit,
        items=[ImpactedFileItem(file_path=f.file_path, reason=f.reason) for f in files],
    )
