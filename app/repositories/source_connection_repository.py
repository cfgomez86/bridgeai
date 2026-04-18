from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.models.source_connection import PlatformConfig, SourceConnection


class SourceConnectionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Platform configs ────────────────────────────────────────────────────

    def get_platform_config(self, platform: str) -> Optional[PlatformConfig]:
        return self._db.query(PlatformConfig).filter(PlatformConfig.platform == platform).first()

    def list_platform_configs(self) -> list[PlatformConfig]:
        return self._db.query(PlatformConfig).all()

    def upsert_platform_config(self, platform: str, client_id: str, client_secret: str) -> PlatformConfig:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        existing = self.get_platform_config(platform)
        if existing:
            existing.client_id = client_id
            existing.client_secret = client_secret
            existing.updated_at = now
            self._db.commit()
            self._db.refresh(existing)
            return existing
        import uuid
        config = PlatformConfig(
            id=str(uuid.uuid4()),
            platform=platform,
            client_id=client_id,
            client_secret=client_secret,
            created_at=now,
            updated_at=now,
        )
        self._db.add(config)
        self._db.commit()
        self._db.refresh(config)
        return config

    def delete_platform_config(self, platform: str) -> bool:
        existing = self.get_platform_config(platform)
        if not existing:
            return False
        self._db.delete(existing)
        self._db.commit()
        return True

    # ── Source connections ──────────────────────────────────────────────────

    def create_pending(self, platform: str, oauth_state: str) -> SourceConnection:
        import uuid
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        conn = SourceConnection(
            id=str(uuid.uuid4()),
            platform=platform,
            oauth_state=oauth_state,
            created_at=now,
        )
        self._db.add(conn)
        self._db.commit()
        self._db.refresh(conn)
        return conn

    def find_by_state(self, oauth_state: str) -> Optional[SourceConnection]:
        return (
            self._db.query(SourceConnection)
            .filter(SourceConnection.oauth_state == oauth_state)
            .first()
        )

    def find_by_id(self, connection_id: str) -> Optional[SourceConnection]:
        return self._db.query(SourceConnection).filter(SourceConnection.id == connection_id).first()

    def list_connected(self) -> list[SourceConnection]:
        return (
            self._db.query(SourceConnection)
            .filter(SourceConnection.display_name != "")
            .filter(SourceConnection.access_token != "")
            .order_by(SourceConnection.created_at.desc())
            .all()
        )

    def get_active(self) -> Optional[SourceConnection]:
        return (
            self._db.query(SourceConnection)
            .filter(SourceConnection.is_active == True)  # noqa: E712
            .first()
        )

    def update_after_oauth(
        self, connection_id: str, display_name: str, access_token: str, refresh_token: str | None
    ) -> Optional[SourceConnection]:
        conn = self.find_by_id(connection_id)
        if not conn:
            return None
        conn.display_name = display_name
        conn.access_token = access_token
        conn.refresh_token = refresh_token
        conn.oauth_state = None
        self._db.commit()
        self._db.refresh(conn)
        return conn

    def activate(
        self, connection_id: str, repo_full_name: str, repo_name: str, owner: str, default_branch: str
    ) -> Optional[SourceConnection]:
        # deactivate all
        self._db.query(SourceConnection).filter(SourceConnection.is_active == True).update(  # noqa: E712
            {"is_active": False}, synchronize_session=False
        )
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
