import logging
import uuid

from app.core.config import Settings, get_settings
from app.domain.source_connection import Repository, SourceConnection
from app.models.source_connection import SourceConnection as SourceConnectionORM
from app.repositories.source_connection_repository import SourceConnectionRepository
from app.services.scm_providers import SUPPORTED_PLATFORMS, get_provider

logger = logging.getLogger(__name__)

_PLATFORM_LABELS = {
    "github": "GitHub",
    "gitlab": "GitLab",
    "azure_devops": "Azure DevOps",
    "bitbucket": "Bitbucket",
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
        mapping = {
            "github": (self._settings.GITHUB_CLIENT_ID, self._settings.GITHUB_CLIENT_SECRET),
            "gitlab": (self._settings.GITLAB_CLIENT_ID, self._settings.GITLAB_CLIENT_SECRET),
            "azure_devops": (self._settings.AZURE_DEVOPS_CLIENT_ID, self._settings.AZURE_DEVOPS_CLIENT_SECRET),
            "bitbucket": (self._settings.BITBUCKET_CLIENT_ID, self._settings.BITBUCKET_CLIENT_SECRET),
        }
        client_id, client_secret = mapping.get(platform, ("", ""))
        if client_id and client_secret:
            return {"client_id": client_id, "client_secret": client_secret}
        return None

    # ── Platform listing ────────────────────────────────────────────────────

    def list_platforms(self) -> list[dict]:
        result = []
        for platform in SUPPORTED_PLATFORMS:
            server_creds = self._get_server_credentials(platform)
            result.append({
                "platform": platform,
                "label": _PLATFORM_LABELS.get(platform, platform),
                "server_configured": server_creds is not None,
            })
        return result

    # ── OAuth flow ──────────────────────────────────────────────────────────

    def _resolve_credentials(self, platform: str) -> tuple[str, str]:
        server = self._get_server_credentials(platform)
        if server:
            return server["client_id"], server["client_secret"]
        raise ValueError(
            f"Platform {platform!r} is not configured. "
            "Set server-side credentials in .env."
        )

    def get_authorize_url(self, platform: str, redirect_uri: str) -> str:
        client_id, _ = self._resolve_credentials(platform)
        provider = get_provider(platform)
        state = str(uuid.uuid4())
        self._repo.create_oauth_state(platform, state, redirect_uri)
        url = provider.get_authorize_url(client_id, redirect_uri, state)
        logger.info("OAuth authorize initiated platform=%s state=%s", platform, state)
        return url

    def handle_callback(self, platform: str, code: str, state: str) -> SourceConnection:
        oauth_state = self._repo.consume_oauth_state(state)
        if not oauth_state:
            # Duplicate callback (browser/proxy double-hit): state already consumed.
            # Restore tenant from the stored record and return the existing connection.
            past = self._repo.find_oauth_state_by_token(state)
            if past:
                from app.core.context import current_tenant_id
                current_tenant_id.set(past.tenant_id)
                existing = self._repo.find_latest_for_platform(platform)
                if existing:
                    logger.info("OAuth duplicate callback platform=%s — returning existing connection", platform)
                    return _to_domain_connection(existing)
            raise ValueError("Invalid or expired OAuth state. Please start the connection flow again.")

        # The callback arrives from GitHub without Auth0 auth, so current_tenant_id is not set.
        # Restore it from the OAuth state record, which was written during the authenticated authorize step.
        from app.core.context import current_tenant_id
        current_tenant_id.set(oauth_state.tenant_id)

        redirect_uri = oauth_state.redirect_uri
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
        orm = self._repo.create_connection(
            platform=platform,
            display_name=user_info["login"],
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
        )
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
