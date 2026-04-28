import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.database.session import Base


class StoryFeedback(Base):
    __tablename__ = "story_feedback"
    __table_args__ = (
        UniqueConstraint("tenant_id", "story_id", "user_id", name="uq_story_feedback_per_user"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False)
    story_id = Column(String(36), ForeignKey("user_stories.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, nullable=False)
    rating = Column(String, nullable=False)   # "thumbs_up" | "thumbs_down"
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
