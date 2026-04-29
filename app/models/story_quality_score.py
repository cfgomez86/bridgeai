import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.database.session import Base


class StoryQualityScore(Base):
    __tablename__ = "story_quality_score"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False)
    story_id = Column(String(36), ForeignKey("user_stories.id", ondelete="CASCADE"), nullable=False, unique=True)
    completeness = Column(Float, nullable=False)
    specificity = Column(Float, nullable=False)
    feasibility = Column(Float, nullable=False)
    risk_coverage = Column(Float, nullable=False)
    language_consistency = Column(Float, nullable=False)
    overall = Column(Float, nullable=False)
    justification = Column(Text, nullable=True)
    judge_model = Column(String, nullable=True)
    dispersion = Column(Float, nullable=True)
    samples_used = Column(Integer, nullable=True)
    evidence = Column(Text, nullable=True)
    evaluated_at = Column(DateTime, default=datetime.utcnow)
