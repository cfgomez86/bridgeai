from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.encrypted_types import EncryptedText
from app.database.session import Base


class SourceConnection(Base):
    __tablename__ = "source_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    access_token: Mapped[str] = mapped_column(EncryptedText, nullable=False, default="")
    refresh_token: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    auth_method: Mapped[str] = mapped_column(String(10), nullable=False, default="oauth")
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    repo_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    repo_full_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    boards_project: Mapped[str | None] = mapped_column(String(512), nullable=True)
    default_branch: Mapped[str] = mapped_column(String(100), nullable=False, default="main")
    base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    oauth_state: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
