from datetime import datetime
from sqlalchemy import DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.session import Base


class UserStory(Base):
    __tablename__ = "user_stories"
    __table_args__ = (
        Index("ix_user_stories_req_analysis", "requirement_id", "impact_analysis_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    requirement_id: Mapped[str] = mapped_column(String(36), nullable=False)
    impact_analysis_id: Mapped[str] = mapped_column(String(36), nullable=False)
    project_id: Mapped[str] = mapped_column(String(255), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, server_default="es")
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    story_description: Mapped[str] = mapped_column(Text, nullable=False)
    acceptance_criteria: Mapped[str] = mapped_column(Text, nullable=False)  # JSON list
    subtasks: Mapped[str] = mapped_column(Text, nullable=True)              # JSON {"frontend":[...],"backend":[...],"configuration":[...]}
    definition_of_done: Mapped[str] = mapped_column(Text, nullable=False)   # JSON list
    risk_notes: Mapped[str] = mapped_column(Text, nullable=False)           # JSON list
    story_points: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)
    generation_time_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
