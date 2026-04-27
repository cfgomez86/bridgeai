from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.context import current_tenant_id, get_tenant_id

_SCM_PLATFORMS = {"github", "gitlab", "azure_devops", "bitbucket"}
from app.models.code_file import CodeFile
from app.models.connection_audit_log import ConnectionAuditLog
from app.models.impact_analysis import ImpactAnalysis, ImpactedFile
from app.models.oauth_state import OAuthState
from app.models.requirement import Requirement
from app.models.source_connection import SourceConnection
from app.models.user_story import UserStory

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
        auth_method: str = "oauth",
        base_url: Optional[str] = None,
    ) -> SourceConnection:
        conn = SourceConnection(
            id=str(uuid4()),
            tenant_id=self._tid(),
            platform=platform,
            display_name=display_name,
            access_token=access_token,
            refresh_token=refresh_token,
            auth_method=auth_method,
            base_url=base_url,
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
        """Return the active SCM connection (GitHub, GitLab, etc.)."""
        return (
            self._db.query(SourceConnection)
            .filter(
                SourceConnection.tenant_id == self._tid(),
                SourceConnection.platform.in_(_SCM_PLATFORMS),
                SourceConnection.is_active == True,  # noqa: E712
            )
            .first()
        )

    def get_active_for_platform(self, platform: str) -> Optional[SourceConnection]:
        return (
            self._db.query(SourceConnection)
            .filter(
                SourceConnection.tenant_id == self._tid(),
                SourceConnection.platform == platform,
                SourceConnection.is_active == True,  # noqa: E712
            )
            .first()
        )

    def activate(
        self, connection_id: str, repo_full_name: str, repo_name: str, owner: str, default_branch: str
    ) -> Optional[SourceConnection]:
        # Deactivate only other SCM connections — ticket connections remain unaffected
        self._db.query(SourceConnection).filter(
            SourceConnection.tenant_id == self._tid(),
            SourceConnection.platform.in_(_SCM_PLATFORMS),
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

    def activate_site(
        self, connection_id: str, cloud_id: str, api_base_url: str, site_url: str, site_name: str
    ) -> Optional[SourceConnection]:
        # Deactivate other Jira connections only
        self._db.query(SourceConnection).filter(
            SourceConnection.tenant_id == self._tid(),
            SourceConnection.platform == "jira",
            SourceConnection.is_active == True,  # noqa: E712
        ).update({"is_active": False}, synchronize_session=False)
        conn = self.find_by_id(connection_id)
        if not conn:
            self._db.commit()
            return None
        conn.is_active = True
        conn.owner = cloud_id
        conn.base_url = api_base_url
        conn.repo_full_name = site_url
        conn.repo_name = site_name
        self._db.commit()
        self._db.refresh(conn)
        return conn

    def delete(self, connection_id: str) -> bool:
        conn = self.find_by_id(connection_id)
        if not conn:
            return False
        # Delete in FK-safe order: children before parents
        self._db.query(UserStory).filter(UserStory.source_connection_id == connection_id).delete(synchronize_session=False)
        self._db.query(ImpactedFile).filter(ImpactedFile.source_connection_id == connection_id).delete(synchronize_session=False)
        self._db.query(ImpactAnalysis).filter(ImpactAnalysis.source_connection_id == connection_id).delete(synchronize_session=False)
        self._db.query(Requirement).filter(Requirement.source_connection_id == connection_id).delete(synchronize_session=False)
        self._db.query(CodeFile).filter(CodeFile.source_connection_id == connection_id).delete(synchronize_session=False)
        self._db.delete(conn)
        self._db.commit()
        return True

    # ── Audit log ───────────────────────────────────────────────────────────

    def log_event(
        self,
        connection_id: str,
        platform: str,
        auth_method: str,
        event: str,
        actor: str,
        detail: Optional[str] = None,
    ) -> None:
        entry = ConnectionAuditLog(
            id=str(uuid4()),
            tenant_id=self._tid(),
            connection_id=connection_id,
            platform=platform,
            auth_method=auth_method,
            event=event,
            actor=actor,
            detail=detail,
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self._db.add(entry)
        self._db.commit()

    def get_audit_logs(self, limit: int = 100) -> list[ConnectionAuditLog]:
        return (
            self._db.query(ConnectionAuditLog)
            .filter(ConnectionAuditLog.tenant_id == self._tid())
            .order_by(ConnectionAuditLog.timestamp.desc())
            .limit(limit)
            .all()
        )

    def get_audit_logs_for_connection(self, connection_id: str) -> list[ConnectionAuditLog]:
        return (
            self._db.query(ConnectionAuditLog)
            .filter(
                ConnectionAuditLog.tenant_id == self._tid(),
                ConnectionAuditLog.connection_id == connection_id,
            )
            .order_by(ConnectionAuditLog.timestamp.desc())
            .all()
        )
