from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.logging import get_logger
from app.database.session import get_db
from app.models.user import User
from app.repositories.impact_analysis_repository import ImpactAnalysisRepository
from app.repositories.requirement_repository import RequirementRepository
from app.repositories.story_feedback_repository import StoryFeedbackRepository
from app.repositories.story_quality_repository import StoryQualityRepository
from app.repositories.ticket_integration_repository import TicketIntegrationRepository
from app.repositories.user_story_repository import UserStoryRepository
from app.services.dashboard_service import DashboardService

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)], tags=["dashboard"])


class DashboardStatsResponse(BaseModel):
    window_days: Optional[int]
    requirements_count: int
    stories_count: int
    impact_analyses_count: int
    tickets_count: int
    conversion_rate: Optional[float]
    feedback_total: int
    feedback_thumbs_up: int
    feedback_thumbs_down: int
    feedback_approval_rate: Optional[float]
    quality_avg_overall: Optional[float]
    quality_evaluated_count: int
    quality_avg_organic: Optional[float] = None
    quality_count_organic: int = 0
    quality_avg_forced: Optional[float] = None
    quality_count_forced: int = 0
    quality_count_creation_bypass: int = 0
    quality_count_override: int = 0
    tickets_failed_count: int = 0
    avg_generation_time_seconds: Optional[float] = None
    unnecessary_force_count: int = 0
    quality_organic_avg_completeness: Optional[float] = None
    quality_organic_avg_specificity: Optional[float] = None
    quality_organic_avg_feasibility: Optional[float] = None
    quality_organic_avg_risk_coverage: Optional[float] = None
    quality_organic_avg_language_consistency: Optional[float] = None
    tickets_by_provider: dict[str, int]
    stories_by_risk: dict[str, int]


class ActivityEventResponse(BaseModel):
    tone: str
    title: str
    meta: str
    time: str
    badge: Optional[str] = None
    link: Optional[str] = None


class NegativeFeedbackItem(BaseModel):
    id: str
    story_id: str
    story_title: str
    user_id: str
    rating: str
    comment: str
    created_at: str


def _service(db: Session, window_days: Optional[int] = None) -> DashboardService:
    return DashboardService(
        story_repo=UserStoryRepository(db),
        requirement_repo=RequirementRepository(db),
        impact_repo=ImpactAnalysisRepository(db),
        ticket_repo=TicketIntegrationRepository(db),
        feedback_repo=StoryFeedbackRepository(db),
        quality_repo=StoryQualityRepository(db),
        window_days=window_days,
    )


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    window_days: Optional[int] = Query(default=None, ge=0),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> DashboardStatsResponse:
    stats = _service(db, window_days=window_days).get_stats()
    return DashboardStatsResponse(
        window_days=stats.window_days,
        requirements_count=stats.requirements_count,
        stories_count=stats.stories_count,
        impact_analyses_count=stats.impact_analyses_count,
        tickets_count=stats.tickets_count,
        conversion_rate=stats.conversion_rate,
        feedback_total=stats.feedback_total,
        feedback_thumbs_up=stats.feedback_thumbs_up,
        feedback_thumbs_down=stats.feedback_thumbs_down,
        feedback_approval_rate=stats.feedback_approval_rate,
        quality_avg_overall=stats.quality_avg_overall,
        quality_evaluated_count=stats.quality_evaluated_count,
        quality_avg_organic=stats.quality_avg_organic,
        quality_count_organic=stats.quality_count_organic,
        quality_avg_forced=stats.quality_avg_forced,
        quality_count_forced=stats.quality_count_forced,
        quality_count_creation_bypass=stats.quality_count_creation_bypass,
        quality_count_override=stats.quality_count_override,
        tickets_failed_count=stats.tickets_failed_count,
        avg_generation_time_seconds=stats.avg_generation_time_seconds,
        unnecessary_force_count=stats.unnecessary_force_count,
        quality_organic_avg_completeness=stats.quality_organic_avg_completeness,
        quality_organic_avg_specificity=stats.quality_organic_avg_specificity,
        quality_organic_avg_feasibility=stats.quality_organic_avg_feasibility,
        quality_organic_avg_risk_coverage=stats.quality_organic_avg_risk_coverage,
        quality_organic_avg_language_consistency=stats.quality_organic_avg_language_consistency,
        tickets_by_provider=stats.tickets_by_provider,
        stories_by_risk=stats.stories_by_risk,
    )


@router.get("/dashboard/activity", response_model=list[ActivityEventResponse])
async def get_dashboard_activity(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[ActivityEventResponse]:
    events = _service(db).get_activity(limit=limit)
    return [
        ActivityEventResponse(
            tone=e.tone, title=e.title, meta=e.meta, time=e.time,
            badge=e.badge, link=e.link,
        )
        for e in events
    ]


@router.get("/feedback/comments", response_model=list[NegativeFeedbackItem])
async def list_feedback_comments(
    rating: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[NegativeFeedbackItem]:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required to view feedback comments",
        )
    valid_ratings = {"thumbs_up", "thumbs_down"}
    if rating is not None and rating not in valid_ratings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"rating must be one of: {', '.join(sorted(valid_ratings))}",
        )
    rows = StoryFeedbackRepository(db).list_with_comments(limit, offset, rating=rating)
    return [
        NegativeFeedbackItem(
            id=str(fb.id),
            story_id=str(fb.story_id),
            story_title=title,
            user_id=fb.user_id,
            rating=fb.rating,
            comment=fb.comment or "",
            created_at=fb.created_at.isoformat() if fb.created_at else "",
        )
        for fb, title in rows
    ]
