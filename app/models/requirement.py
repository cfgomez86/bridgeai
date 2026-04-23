from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database.session import Base


class Requirement(Base):
    __tablename__ = "requirements"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "source_connection_id", "requirement_text_hash", "project_id",
            name="uq_requirements_tenant_connection_hash_project",
        ),
        Index(
            "ix_requirements_tenant_connection_project",
            "tenant_id", "source_connection_id", "project_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    source_connection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("source_connections.id"), nullable=False, index=True
    )
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    requirement_text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[str] = mapped_column(String(255), nullable=False)
    intent: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity: Mapped[str] = mapped_column(String(255), nullable=False)
    feature_type: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    business_domain: Mapped[str] = mapped_column(String(100), nullable=False)
    technical_scope: Mapped[str] = mapped_column(String(50), nullable=False)
    estimated_complexity: Mapped[str] = mapped_column(String(10), nullable=False)
    keywords: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-serialized list
    processing_time_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
