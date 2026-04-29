import logging
import urllib.error
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
    "azure_devops": "Azure Repos",
    "bitbucket": "Bitbucket",
    "jira": "Jira",
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
        boards_project=orm.boards_project,
        auth_method=orm.auth_method,
    )


class SourceConnectionService:
    def __init__(
        self,
        repo: SourceConnectionRepository,
        settings: Settings | None = None,
    ) -> None:
        self._repo = repo
        self._settings = settings or get_settings()

    def _get_server_credentials(self, platform: str) -> dict | None:
        mapping = {
            "github": (self._settings.GITHUB_CLIENT_ID, self._settings.GITHUB_CLIENT_SECRET),
            "gitlab": (self._settings.GITLAB_CLIENT_ID, self._settings.GITLAB_CLIENT_SECRET),
            "azure_devops": (self._settings.AZURE_DEVOPS_CLIENT_ID, self._settings.AZURE_DEVOPS_CLIENT_SECRET),
            "bitbucket": (self._settings.BITBUCKET_CLIENT_ID, self._settings.BITBUCKET_CLIENT_SECRET),
            "jira": (self._settings.JIRA_CLIENT_ID, self._settings.JIRA_CLIENT_SECRET),
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
        self._repo.log_event(
            connection_id=orm.id,
            platform=platform,
            auth_method="oauth",
            event="connection_created",
            actor=user_info["login"],
        )
        logger.info("OAuth callback success platform=%s user=%s", platform, user_info["login"])
        return _to_domain_connection(orm)

    # ── PAT connection ──────────────────────────────────────────────────────

    def create_pat_connection(
        self,
        platform: str,
        token: str,
        org_url: str | None = None,
        base_url: str | None = None,
        email: str | None = None,
    ) -> SourceConnection:
        provider = get_provider(platform)
        try:
            user_info = provider.validate_pat(token, org_url=org_url, base_url=base_url, email=email)  # type: ignore[call-arg]
        except Exception as exc:
            raise ValueError(f"PAT validation failed: {exc}") from exc

        display_name = user_info.get("login") or user_info.get("display_name", "")
        stored_base_url = org_url or base_url or None
        orm = self._repo.create_connection(
            platform=platform,
            display_name=display_name,
            access_token=token,
            refresh_token=None,
            auth_method="pat",
            base_url=stored_base_url,
        )
        self._repo.log_event(
            connection_id=orm.id,
            platform=platform,
            auth_method="pat",
            event="connection_created",
            actor=display_name,
        )
        logger.info("PAT connection created platform=%s user=%s", platform, display_name)
        return _to_domain_connection(orm)

    # ── Connections ─────────────────────────────────────────────────────────

    def list_connections(self) -> list[SourceConnection]:
        return [_to_domain_connection(c) for c in self._repo.list_connected()]

    def delete_connection(self, connection_id: str) -> bool:
        conn = self._repo.find_by_id(connection_id)
        if conn:
            self._repo.log_event(
                connection_id=conn.id,
                platform=conn.platform,
                auth_method=conn.auth_method,
                event="connection_deleted",
                actor=conn.display_name,
            )
        return self._repo.delete(connection_id)

    def list_repos(self, connection_id: str) -> list[Repository]:
        conn = self._repo.find_by_id(connection_id)
        if not conn or not conn.access_token:
            raise ValueError(f"Connection {connection_id!r} not found or not authenticated.")
        provider = get_provider(conn.platform)
        kwargs: dict = {}
        if conn.platform == "azure_devops" and conn.base_url:
            kwargs["org_url"] = conn.base_url
        elif conn.platform in ("github", "gitlab", "bitbucket") and conn.base_url:
            kwargs["base_url"] = conn.base_url
        raw = provider.list_repos(conn.access_token, **kwargs)
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
        import json as _json
        self._repo.log_event(
            connection_id=orm.id,
            platform=orm.platform,
            auth_method=orm.auth_method,
            event="repo_activated",
            actor=orm.display_name,
            detail=_json.dumps({"repo": repo_full_name, "branch": default_branch}),
        )
        logger.info("Repo activated connection=%s repo=%s", connection_id, repo_full_name)
        return _to_domain_connection(orm)

    def get_active_connection(self) -> SourceConnection | None:
        orm = self._repo.get_active()
        return _to_domain_connection(orm) if orm else None

    def list_audit_logs(self, connection_id: str | None = None) -> list[dict]:
        if connection_id:
            entries = self._repo.get_audit_logs_for_connection(connection_id)
        else:
            entries = self._repo.get_audit_logs()
        return [
            {
                "id": e.id,
                "connection_id": e.connection_id,
                "platform": e.platform,
                "auth_method": e.auth_method,
                "event": e.event,
                "actor": e.actor,
                "detail": e.detail,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in entries
        ]

    def list_projects(self, connection_id: str) -> list[dict]:
        conn = self._repo.find_by_id(connection_id)
        if not conn or not conn.access_token:
            raise ValueError(f"Connection {connection_id!r} not found or not authenticated.")
        if conn.platform != "azure_devops":
            raise ValueError(f"Project listing is only supported for azure_devops, not {conn.platform!r}")
        provider = get_provider(conn.platform)
        kwargs: dict = {}
        if conn.base_url:
            kwargs["org_url"] = conn.base_url
        return provider.list_projects(conn.access_token, **kwargs)  # type: ignore[attr-defined]

    def _refresh_jira_token(self, conn) -> str:
        """Exchange the stored refresh_token for a new access_token and persist it."""
        if not conn.refresh_token:
            raise ValueError("Jira token expired and no refresh token is available — please reconnect.")
        client_id, client_secret = self._resolve_credentials("jira")
        provider = get_provider("jira")
        tokens = provider.refresh_access_token(conn.refresh_token, client_id, client_secret)  # type: ignore[attr-defined]
        self._repo.update_tokens(conn.id, tokens["access_token"], tokens.get("refresh_token") or conn.refresh_token)
        logger.info("Jira token refreshed connection=%s", conn.id)
        return tokens["access_token"]

    def list_sites(self, connection_id: str) -> list[dict]:
        conn = self._repo.find_by_id(connection_id)
        if not conn or conn.platform != "jira":
            raise ValueError(f"Jira connection {connection_id!r} not found.")
        provider = get_provider("jira")
        try:
            return provider.list_sites(conn.access_token)  # type: ignore[attr-defined]
        except urllib.error.HTTPError as exc:
            if exc.code == 401 and conn.refresh_token:
                new_token = self._refresh_jira_token(conn)
                return provider.list_sites(new_token)  # type: ignore[attr-defined]
            raise

    def list_jira_projects(self, connection_id: str) -> list[dict]:
        conn = self._repo.find_by_id(connection_id)
        if not conn or conn.platform != "jira":
            raise ValueError(f"Jira connection {connection_id!r} not found.")
        if not conn.base_url:
            raise ValueError("No Jira site selected for this connection.")
        provider = get_provider("jira")
        try:
            return provider.list_projects(conn.access_token, conn.base_url)  # type: ignore[attr-defined]
        except urllib.error.HTTPError as exc:
            if exc.code == 401 and conn.refresh_token:
                new_token = self._refresh_jira_token(conn)
                return provider.list_projects(new_token, conn.base_url)  # type: ignore[attr-defined]
            raise

    def get_project_process(self, connection_id: str, project_name: str) -> str:
        """Returns the Azure DevOps process template name for the given project."""
        conn = self._repo.find_by_id(connection_id)
        if not conn or not conn.access_token:
            raise ValueError(f"Connection {connection_id!r} not found or not authenticated.")
        if conn.platform != "azure_devops":
            raise ValueError("get_project_process is only supported for azure_devops connections.")
        # Derive org_url: PAT stores it in base_url; OAuth stores it in boards_project
        org_url = conn.base_url or ""
        if not org_url and conn.boards_project:
            org = conn.boards_project.split("/")[0]
            org_url = f"https://dev.azure.com/{org}"
        if not org_url:
            return ""
        provider = get_provider(conn.platform)
        return provider.get_project_process(conn.access_token, org_url, project_name)  # type: ignore[attr-defined]

    def activate_boards_project(self, connection_id: str, project_full_name: str) -> SourceConnection:
        orm = self._repo.activate_boards_project(connection_id, project_full_name)
        if not orm:
            raise ValueError(f"Connection {connection_id!r} not found.")
        logger.info("Azure Boards project activated connection=%s project=%s", connection_id, project_full_name)
        return _to_domain_connection(orm)

    def activate_site(
        self, connection_id: str, cloud_id: str, api_base_url: str, site_url: str, site_name: str
    ) -> SourceConnection:
        orm = self._repo.activate_site(connection_id, cloud_id, api_base_url, site_url, site_name)
        if not orm:
            raise ValueError(f"Connection {connection_id!r} not found.")
        logger.info("Jira site activated connection=%s site=%s", connection_id, site_name)
        return _to_domain_connection(orm)
