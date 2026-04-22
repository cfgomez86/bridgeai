from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.context import current_tenant_id, get_tenant_id
from app.models.oauth_state import OAuthState
from app.models.source_connection import SourceConnection

_OAUTH_STATE_TTL_MINUTES = 10


class SourceConnectionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _tid(self) -> str:
        return get_tenant_id()

    # ── OAuth state (DB-backed) ────────────────────────────────────────────

    def create_oauth_state(self, platform: str, state_token: str, redirect_uri: str) -> OAuthState:
        record = OAuthState(
            id=str(uuid4()),
            tenant_id=self._tid(),
            platform=platform,
            state_token=state_token,
            redirect_uri=redirect_uri,
            expires_at=datetime.utcnow() + timedelta(minutes=_OAUTH_STATE_TTL_MINUTES),
            consumed=False,
        )
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        return record

    def consume_oauth_state(self, state_token: str) -> Optional[OAuthState]:
        """Find a valid (non-expired, non-consumed) state, mark it consumed and return it."""
        record = (
            self._db.query(OAuthState)
            .filter(
                OAuthState.state_token == state_token,
                OAuthState.consumed == False,  # noqa: E712
                OAuthState.expires_at > datetime.utcnow(),
            )
            .first()
        )
        if not record:
            return None
        record.consumed = True
        self._db.commit()
        return record

    def find_oauth_state_by_token(self, state_token: str) -> Optional[OAuthState]:
        """Find any state by token regardless of consumed/expired status — for idempotent callbacks."""
        return (
            self._db.query(OAuthState)
            .filter(OAuthState.state_token == state_token)
            .first()
        )

    def find_latest_for_platform(self, platform: str) -> Optional[SourceConnection]:
        """Return the most recently created connection for a platform, any status."""
        return (
            self._db.query(SourceConnection)
            .filter(SourceConnection.tenant_id == get_tenant_id(), SourceConnection.platform == platform)
            .order_by(SourceConnection.created_at.desc())
            .first()
        )

    # ── Source connections ──────────────────────────────────────────────────

    def create_connection(
        self,
        platform: str,
        display_name: str,
        access_token: str,
        refresh_token: Optional[str],
    ) -> SourceConnection:
        conn = SourceConnection(
            id=str(uuid4()),
            tenant_id=self._tid(),
            platform=platform,
            display_name=display_name,
            access_token=access_token,
            refresh_token=refresh_token,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self._db.add(conn)
        self._db.commit()
        self._db.refresh(conn)
        return conn

    def find_by_id(self, connection_id: str) -> Optional[SourceConnection]:
        return (
            self._db.query(SourceConnection)
            .filter(SourceConnection.id == connection_id, SourceConnection.tenant_id == self._tid())
            .first()
        )

    def list_connected(self) -> list[SourceConnection]:
        return (
            self._db.query(SourceConnection)
            .filter(
                SourceConnection.tenant_id == self._tid(),
                SourceConnection.display_name != "",
                SourceConnection.access_token != "",
            )
            .order_by(SourceConnection.created_at.desc())
            .all()
        )

    def get_active(self) -> Optional[SourceConnection]:
        return (
            self._db.query(SourceConnection)
            .filter(SourceConnection.tenant_id == self._tid(), SourceConnection.is_active == True)  # noqa: E712
            .first()
        )

    def activate(
        self, connection_id: str, repo_full_name: str, repo_name: str, owner: str, default_branch: str
    ) -> Optional[SourceConnection]:
        self._db.query(SourceConnection).filter(
            SourceConnection.tenant_id == self._tid(),
            SourceConnection.is_active == True,  # noqa: E712
        ).update({"is_active": False}, synchronize_session=False)
        conn = self.find_by_id(connection_id)
        if not conn:
            self._db.commit()
            return None
        conn.is_active = True
        conn.repo_full_name = repo_full_name
        conn.repo_name = repo_name
        conn.owner = owner
        conn.default_branch = default_branch
        self._db.commit()
        self._db.refresh(conn)
        return conn

    def delete(self, connection_id: str) -> bool:
        conn = self.find_by_id(connection_id)
        if not conn:
            return False
        self._db.delete(conn)
        self._db.commit()
        return True
