from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.context import get_tenant_id
from app.models.story_feedback import StoryFeedback


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
