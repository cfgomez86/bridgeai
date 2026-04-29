from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from app.repositories.impact_analysis_repository import ImpactAnalysisRepository
from app.repositories.requirement_repository import RequirementRepository
from app.repositories.story_feedback_repository import StoryFeedbackRepository
from app.repositories.story_quality_repository import StoryQualityRepository
from app.repositories.ticket_integration_repository import TicketIntegrationRepository
from app.repositories.user_story_repository import UserStoryRepository

ActivityTone = Literal["ok", "accent", "warn", "neutral"]


@dataclass(frozen=True)
class DashboardStats:
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
    tickets_by_provider: dict[str, int] = field(default_factory=dict)
    stories_by_risk: dict[str, int] = field(
        default_factory=lambda: {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    )


@dataclass(frozen=True)
class ActivityEvent:
    tone: ActivityTone
    title: str
    meta: str
    time: str  # ISO 8601
    badge: Optional[str] = None
    link: Optional[str] = None


class DashboardService:
    def __init__(
        self,
        story_repo: UserStoryRepository,
        requirement_repo: RequirementRepository,
        impact_repo: ImpactAnalysisRepository,
        ticket_repo: TicketIntegrationRepository,
        feedback_repo: StoryFeedbackRepository,
        quality_repo: StoryQualityRepository,
        window_days: Optional[int] = None,
    ) -> None:
        self._story_repo = story_repo
        self._requirement_repo = requirement_repo
        self._impact_repo = impact_repo
        self._ticket_repo = ticket_repo
        self._feedback_repo = feedback_repo
        self._quality_repo = quality_repo
        self._window_days = window_days

    def _since(self) -> Optional[datetime]:
        if self._window_days is None or self._window_days <= 0:
            return None
        return datetime.now(timezone.utc) - timedelta(days=self._window_days)

    def get_stats(self) -> DashboardStats:
        since = self._since()
        feedback_counts = self._feedback_repo.aggregate_rating_since(since)
        feedback_total = feedback_counts["total"]
        approval_rate = (
            feedback_counts["thumbs_up"] / feedback_total
            if feedback_total > 0
            else None
        )
        stories_count = self._story_repo.count_since(since)
        tickets_count = self._ticket_repo.count_successful_since(since)
        conversion_rate = (
            tickets_count / stories_count if stories_count > 0 else None
        )
        return DashboardStats(
            window_days=self._window_days,
            requirements_count=self._requirement_repo.count_since(since),
            stories_count=stories_count,
            impact_analyses_count=self._impact_repo.count_since(since),
            tickets_count=tickets_count,
            conversion_rate=conversion_rate,
            feedback_total=feedback_total,
            feedback_thumbs_up=feedback_counts["thumbs_up"],
            feedback_thumbs_down=feedback_counts["thumbs_down"],
            feedback_approval_rate=approval_rate,
            quality_avg_overall=self._quality_repo.avg_overall_since(since),
            quality_evaluated_count=self._quality_repo.count_evaluated_since(since),
            tickets_by_provider=self._ticket_repo.count_by_provider_since(since),
            stories_by_risk=self._story_repo.count_by_risk_since(since),
        )

    def get_activity(self, limit: int = 10) -> list[ActivityEvent]:
        per_source_limit = max(limit, 5)
        events: list[ActivityEvent] = []

        for story in self._story_repo.list_recent(per_source_limit):
            events.append(
                ActivityEvent(
                    tone="accent",
                    title=story.title,
                    meta=f"Historia · {story.story_points} pt · {story.risk_level.lower()}",
                    time=_iso(story.created_at),
                    link=f"/workflow?story_id={story.id}",
                )
            )

        for ticket in self._ticket_repo.list_recent_created(per_source_limit):
            external = ticket.external_ticket_id or ""
            tone: ActivityTone = "ok"
            title = f"Ticket creado en {ticket.provider.replace('_', ' ').title()}"
            if external:
                title = f"{external} creado en {ticket.provider.replace('_', ' ').title()}"
            events.append(
                ActivityEvent(
                    tone=tone,
                    title=title,
                    meta=f"{ticket.project_key} · {ticket.issue_type}",
                    time=_iso(ticket.created_at),
                    badge=ticket.provider,
                    link=f"/workflow?story_id={ticket.story_id}",
                )
            )

        for analysis in self._impact_repo.list_recent(per_source_limit):
            tone = _risk_to_tone(analysis.risk_level)
            events.append(
                ActivityEvent(
                    tone=tone,
                    title=f"Análisis de impacto · riesgo {analysis.risk_level.lower()}",
                    meta=f"{analysis.files_impacted} archivos · {analysis.modules_impacted} módulos",
                    time=_iso(analysis.created_at),
                )
            )

        for feedback, story_title in self._feedback_repo.list_negative_with_comments(
            per_source_limit, 0
        ):
            comment = (feedback.comment or "").strip()
            preview = comment if len(comment) <= 80 else comment[:77] + "..."
            events.append(
                ActivityEvent(
                    tone="warn",
                    title=f"Feedback negativo · {story_title}",
                    meta=preview or "Sin comentario",
                    time=_iso(feedback.created_at),
                    link=f"/workflow?story_id={feedback.story_id}",
                )
            )

        events.sort(key=lambda e: e.time, reverse=True)
        return events[:limit]


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _risk_to_tone(risk_level: str) -> ActivityTone:
    risk = (risk_level or "").upper()
    if risk == "HIGH":
        return "warn"
    if risk == "LOW":
        return "ok"
    return "neutral"
