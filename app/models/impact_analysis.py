from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.session import Base


class ImpactAnalysis(Base):
    __tablename__ = "impact_analysis"
    __table_args__ = (
        Index("ix_impact_analysis_tenant_connection", "tenant_id", "source_connection_id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    source_connection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("source_connections.id"), nullable=False, index=True
    )
    requirement: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)
    files_impacted: Mapped[int] = mapped_column(Integer, nullable=False)
    modules_impacted: Mapped[int] = mapped_column(Integer, nullable=False)
    analysis_summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ImpactedFile(Base):
    __tablename__ = "impacted_files"
    __table_args__ = (
        Index("ix_impacted_files_tenant_connection", "tenant_id", "source_connection_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(String(36), ForeignKey("impact_analysis.id"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    source_connection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("source_connections.id"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
