from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.session import Base


class ConnectionAuditLog(Base):
    __tablename__ = "connection_audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    # Plain string — not a FK so the log survives connection deletion
    connection_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    auth_method: Mapped[str] = mapped_column(String(10), nullable=False)
    event: Mapped[str] = mapped_column(String(50), nullable=False)   # connection_created | repo_activated | connection_deleted
    actor: Mapped[str] = mapped_column(String(255), nullable=False)  # display_name at the time of event
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON — repo name, error, etc.
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
