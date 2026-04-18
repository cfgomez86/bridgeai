import logging
import uuid

from app.core.config import Settings, get_settings
from app.domain.source_connection import PlatformConfig, Repository, SourceConnection
from app.models.source_connection import PlatformConfig as PlatformConfigORM
from app.models.source_connection import SourceConnection as SourceConnectionORM
from app.repositories.source_connection_repository import SourceConnectionRepository
from app.services.scm_providers import SUPPORTED_PLATFORMS, get_provider

logger = logging.getLogger(__name__)

_PLATFORM_LABELS = {
    "github": "GitHub",
    "gitlab": "GitLab",
    "azure_devops": "Azure DevOps",
}


def _to_domain_connection(orm: SourceConnectionORM) -> SourceConnection:
    return SourceConnection(
        id=orm.id,
        platform=orm.platform,
        display_name=orm.display_name,
        repo_full_name=orm.repo_full_name,
        repo_name=orm.repo_name,
        owner=orm.owner,
        default_branch=orm.default_branch,
        is_active=orm.is_active,
        created_at=orm.created_at,
    )


class SourceConnectionService:
    def __init__(
        self,
        repo: SourceConnectionRepository,
        settings: Settings = get_settings(),  # type: ignore[assignment]
    ) -> None:
        self._repo = repo
        self._settings = settings

    def _redirect_uri(self, platform: str) -> str:
        api_base = self._settings.API_BASE_URL.rstrip("/")
        return f"{api_base}/api/v1/connections/oauth/callback/{platform}"

    # ── Platform configs ────────────────────────────────────────────────────

    def list_platforms(self) -> list[dict]:
        configs = {c.platform: c for c in self._repo.list_platform_configs()}
        result = []
        for platform in SUPPORTED_PLATFORMS:
            config = configs.get(platform)
            result.append({
                "platform": platform,
                "label": _PLATFORM_LABELS.get(platform, platform),
                "configured": config is not None,
                "client_id": config.client_id if config else None,
            })
        return result

    def save_platform_config(self, platform: str, client_id: str, client_secret: str) -> PlatformConfig:
        if platform not in SUPPORTED_PLATFORMS:
            raise ValueError(f"Unsupported platform: {platform!r}")
        orm = self._repo.upsert_platform_config(platform, client_id, client_secret)
        return PlatformConfig(platform=orm.platform, client_id=orm.client_id, configured=True)

    def delete_platform_config(self, platform: str) -> bool:
        return self._repo.delete_platform_config(platform)

    # ── OAuth flow ──────────────────────────────────────────────────────────

    def get_authorize_url(self, platform: str) -> str:
        config = self._repo.get_platform_config(platform)
        if not config:
            raise ValueError(f"Platform {platform!r} is not configured. Set client_id and client_secret first.")
        provider = get_provider(platform)
        state = str(uuid.uuid4())
        self._repo.create_pending(platform, state)
        redirect_uri = self._redirect_uri(platform)
        url = provider.get_authorize_url(config.client_id, redirect_uri, state)
        logger.info("OAuth authorize initiated platform=%s state=%s", platform, state)
        return url

    def handle_callback(self, platform: str, code: str, state: str) -> SourceConnection:
        pending = self._repo.find_by_state(state)
        if not pending:
            raise ValueError("Invalid or expired OAuth state parameter.")
        config = self._repo.get_platform_config(platform)
        if not config:
            raise ValueError(f"Platform {platform!r} config not found.")
        provider = get_provider(platform)
        redirect_uri = self._redirect_uri(platform)
        tokens = provider.exchange_code(code, config.client_id, config.client_secret, redirect_uri)
        user_info = provider.get_user_info(tokens["access_token"])
        orm = self._repo.update_after_oauth(
            pending.id,
            display_name=user_info["login"],
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
        )
        if not orm:
            raise ValueError("Connection record not found after OAuth exchange.")
        logger.info("OAuth callback success platform=%s user=%s", platform, user_info["login"])
        return _to_domain_connection(orm)

    # ── Connections ─────────────────────────────────────────────────────────

    def list_connections(self) -> list[SourceConnection]:
        return [_to_domain_connection(c) for c in self._repo.list_connected()]

    def delete_connection(self, connection_id: str) -> bool:
        return self._repo.delete(connection_id)

    def list_repos(self, connection_id: str) -> list[Repository]:
        conn = self._repo.find_by_id(connection_id)
        if not conn or not conn.access_token:
            raise ValueError(f"Connection {connection_id!r} not found or not authenticated.")
        provider = get_provider(conn.platform)
        raw = provider.list_repos(conn.access_token)
        return [
            Repository(
                full_name=r["full_name"],
                name=r["name"],
                owner=r["owner"],
                default_branch=r["default_branch"],
                private=r["private"],
            )
            for r in raw
        ]

    def activate_repo(
        self, connection_id: str, repo_full_name: str, default_branch: str
    ) -> SourceConnection:
        parts = repo_full_name.split("/")
        repo_name = parts[-1]
        owner = parts[0] if len(parts) >= 2 else ""
        orm = self._repo.activate(connection_id, repo_full_name, repo_name, owner, default_branch)
        if not orm:
            raise ValueError(f"Connection {connection_id!r} not found.")
        logger.info("Repo activated connection=%s repo=%s", connection_id, repo_full_name)
        return _to_domain_connection(orm)

    def get_active_connection(self) -> SourceConnection | None:
        orm = self._repo.get_active()
        return _to_domain_connection(orm) if orm else None
