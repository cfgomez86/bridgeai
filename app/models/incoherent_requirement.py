from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class IncoherentRequirement(Base):
    __tablename__ = "incoherent_requirements"
    __table_args__ = (
        Index(
            "ix_incoherent_requirements_tenant_created",
            "tenant_id",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    requirement_text_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason_codes: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-serialized list
    project_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_connection_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
