from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.context import get_tenant_id
from app.models.story_feedback import StoryFeedback
from app.models.user_story import UserStory
from app.models.user import User


class StoryFeedbackRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _tid(self) -> str:
        return get_tenant_id()

    def upsert(
        self,
        story_id: str,
        user_id: str,
        rating: str,
        comment: Optional[str],
    ) -> StoryFeedback:
        """Insert or update feedback for a given story/user pair."""
        now = datetime.utcnow()
        tid = self._tid()

        existing = self.find_by_user(story_id, user_id)
        if existing:
            existing.rating = rating
            existing.comment = comment
            existing.updated_at = now
            self._db.commit()
            self._db.refresh(existing)
            return existing

        record = StoryFeedback(
            tenant_id=tid,
            story_id=story_id,
            user_id=user_id,
            rating=rating,
            comment=comment,
            created_at=now,
            updated_at=now,
        )
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        return record

    def find_by_user(self, story_id: str, user_id: str) -> Optional[StoryFeedback]:
        return (
            self._db.query(StoryFeedback)
            .filter(
                StoryFeedback.tenant_id == self._tid(),
                StoryFeedback.story_id == story_id,
                StoryFeedback.user_id == user_id,
            )
            .first()
        )

    def aggregate_rating_since(self, since: Optional[datetime]) -> dict[str, int]:
        q = (
            self._db.query(StoryFeedback.rating, func.count(StoryFeedback.id))
            .filter(StoryFeedback.tenant_id == self._tid())
        )
        if since is not None:
            q = q.filter(StoryFeedback.created_at >= since)
        rows = q.group_by(StoryFeedback.rating).all()
        counts = {"thumbs_up": 0, "thumbs_down": 0}
        for rating, count in rows:
            counts[rating] = count
        counts["total"] = counts["thumbs_up"] + counts["thumbs_down"]
        return counts

    def list_negative_with_comments(
        self, limit: int, offset: int
    ) -> list[tuple[StoryFeedback, str]]:
        return self.list_with_comments(limit, offset, rating="thumbs_down")

    def list_with_comments(
        self,
        limit: int,
        offset: int,
        rating: Optional[str] = None,
        user_id: Optional[str] = None,
        since: Optional[datetime] = None,
        skip_tenant_filter: bool = False,
    ) -> tuple[list[tuple[StoryFeedback, str, Optional[str]]], int]:
        tid = self._tid() if not skip_tenant_filter else None

        q = self._db.query(StoryFeedback, UserStory.title)
        if not skip_tenant_filter:
            q = q.filter(StoryFeedback.tenant_id == tid)
        q = q.join(UserStory, UserStory.id == StoryFeedback.story_id)
        if not skip_tenant_filter:
            q = q.filter(UserStory.tenant_id == tid)

        if rating:
            q = q.filter(StoryFeedback.rating == rating)
        if user_id:
            q = q.filter(StoryFeedback.user_id == user_id)
        if since:
            q = q.filter(StoryFeedback.created_at >= since)

        total = (
            q.with_entities(func.count(StoryFeedback.id)).scalar() or 0
        )

        rows = self._db.query(StoryFeedback, UserStory.title, User.email)
        if not skip_tenant_filter:
            rows = rows.filter(StoryFeedback.tenant_id == tid)
        rows = rows.outerjoin(UserStory, UserStory.id == StoryFeedback.story_id)
        if not skip_tenant_filter:
            rows = rows.filter(UserStory.tenant_id == tid)
        rows = rows.outerjoin(User, User.id == StoryFeedback.user_id)

        if rating:
            rows = rows.filter(StoryFeedback.rating == rating)
        if user_id:
            rows = rows.filter(StoryFeedback.user_id == user_id)
        if since:
            rows = rows.filter(StoryFeedback.created_at >= since)

        rows = (
            rows.order_by(StoryFeedback.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [(fb, title, email) for fb, title, email in rows], int(total)

    def list_recent(self, limit: int) -> list[StoryFeedback]:
        return (
            self._db.query(StoryFeedback)
            .filter(StoryFeedback.tenant_id == self._tid())
            .order_by(StoryFeedback.created_at.desc())
            .limit(limit)
            .all()
        )
