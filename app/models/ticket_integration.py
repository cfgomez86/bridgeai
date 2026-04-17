from datetime import datetime
from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.session import Base


class TicketIntegration(Base):
    __tablename__ = "ticket_integrations"
    __table_args__ = (
        Index("ix_ticket_integrations_story_provider", "story_id", "provider"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    story_id: Mapped[str] = mapped_column(String(36), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    project_key: Mapped[str] = mapped_column(String(100), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(100), nullable=False)
    external_ticket_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class IntegrationAuditLog(Base):
    __tablename__ = "integration_audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    story_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)   # JSON
    response: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
