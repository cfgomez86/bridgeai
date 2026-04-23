from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class CodeFile(Base):
    __tablename__ = "code_files"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "source_connection_id", "file_path",
            name="uq_code_files_tenant_connection_path",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    source_connection_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("source_connections.id"), nullable=True, index=True
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    extension: Mapped[str] = mapped_column(String(20), nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_modified: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    lines_of_code: Mapped[int] = mapped_column(Integer, nullable=False)
    indexed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
