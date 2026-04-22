from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class OAuthState(Base):
    __tablename__ = "oauth_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    state_token: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    redirect_uri: Mapped[str] = mapped_column(String(2048), nullable=False, default="")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    consumed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
