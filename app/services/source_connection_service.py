import logging
import time
import uuid

from app.core.config import Settings, get_settings
from app.domain.source_connection import PlatformConfig, Repository, SourceConnection
from app.models.source_connection import PlatformConfig as PlatformConfigORM
from app.models.source_connection import SourceConnection as SourceConnectionORM
from app.repositories.source_connection_repository import SourceConnectionRepository
from app.services.scm_providers import SUPPORTED_PLATFORMS, get_provider

logger = logging.getLogger(__name__)

# redirect_uri store keyed by oauth_state UUID, with creation timestamp for TTL.
# Single-process only; multi-process deployments need a shared store (Redis).
_oauth_redirect_cache: dict[str, tuple[str, float]] = {}
_OAUTH_STATE_TTL = 600  # 10 minutes


def _prune_oauth_cache() -> None:
    now = time.monotonic()
    stale = [k for k, (_, ts) in _oauth_redirect_cache.items() if now - ts > _OAUTH_STATE_TTL]
    for k in stale:
        _oauth_redirect_cache.pop(k, None)

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

    def _get_server_credentials(self, platform: str) -> dict | None:
        """Return first-party OAuth credentials from .env, or None if not set."""
        mapping = {
            "github": (self._settings.GITHUB_CLIENT_ID, self._settings.GITHUB_CLIENT_SECRET),
            "gitlab": (self._settings.GITLAB_CLIENT_ID, self._settings.GITLAB_CLIENT_SECRET),
            "azure_devops": (self._settings.AZURE_DEVOPS_CLIENT_ID, self._settings.AZURE_DEVOPS_CLIENT_SECRET),
        }
        client_id, client_secret = mapping.get(platform, ("", ""))
        if client_id and client_secret:
            return {"client_id": client_id, "client_secret": client_secret}
        return None

    # ── Platform configs ────────────────────────────────────────────────────

    def list_platforms(self) -> list[dict]:
        configs = {c.platform: c for c in self._repo.list_platform_configs()}
        result = []
        for platform in SUPPORTED_PLATFORMS:
            config = configs.get(platform)
            server_creds = self._get_server_credentials(platform)
            result.append({
                "platform": platform,
                "label": _PLATFORM_LABELS.get(platform, platform),
                "configured": config is not None,
                "client_id": config.client_id if config else None,
                "server_configured": server_creds is not None,
                "redirect_uri": None,  # Now computed dynamically via /oauth/redirect-uri/{platform}
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

    def _resolve_credentials(self, platform: str) -> tuple[str, str]:
        """Return (client_id, client_secret): user DB config takes priority, then server .env."""
        config = self._repo.get_platform_config(platform)
        if config:
            return config.client_id, config.client_secret
        server = self._get_server_credentials(platform)
        if server:
            return server["client_id"], server["client_secret"]
        raise ValueError(
            f"Platform {platform!r} is not configured. "
            "Either set client_id/secret in the UI or configure server-side credentials in .env."
        )

    def get_authorize_url(self, platform: str, redirect_uri: str) -> str:
        client_id, _ = self._resolve_credentials(platform)
        provider = get_provider(platform)
        state = str(uuid.uuid4())
        self._repo.create_pending(platform, state)
        _prune_oauth_cache()
        _oauth_redirect_cache[state] = (redirect_uri, time.monotonic())
        url = provider.get_authorize_url(client_id, redirect_uri, state)
        logger.info("OAuth authorize initiated platform=%s state=%s mode=%s",
                    platform, state, "byoa" if self._repo.get_platform_config(platform) else "server")
        return url

    def handle_callback(self, platform: str, code: str, state: str) -> SourceConnection:
        pending = self._repo.find_by_state(state)
        if not pending:
            raise ValueError("Invalid or expired OAuth state parameter.")
        cached = _oauth_redirect_cache.pop(state, None)
        if not cached:
            raise ValueError(
                "OAuth session expired or server was restarted. Please start the connection flow again."
            )
        redirect_uri, _ = cached
        client_id, client_secret = self._resolve_credentials(platform)
        provider = get_provider(platform)
        try:
            tokens = provider.exchange_code(code, client_id, client_secret, redirect_uri)
        except ValueError:
            raise
        except Exception as exc:
            logger.error("OAuth token exchange failed platform=%s error=%s", platform, exc)
            raise ValueError("OAuth token exchange failed. Please try again.") from exc
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
