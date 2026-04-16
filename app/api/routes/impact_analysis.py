import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
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
    modules_impacted: int
    risk_level: str
    duration_seconds: float
    request_id: str


def get_impact_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ImpactAnalysisService:
    code_repo = CodeFileRepository(db)
    impact_repo = ImpactAnalysisRepository(db)
    return ImpactAnalysisService(code_repo, impact_repo, settings.PROJECT_ROOT, DependencyAnalyzer())


@router.post("/impact-analysis", response_model=ImpactAnalysisResponse)
def analyze_impact(
    body: ImpactAnalysisRequest,
    service: ImpactAnalysisService = Depends(get_impact_service),
) -> ImpactAnalysisResponse:
    request_id: str = str(uuid.uuid4())
    logger.info("POST /impact-analysis started request_id=%s requirement=%r", request_id, body.requirement)
    try:
        result = service.analyze(body.requirement, body.project_id)
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
