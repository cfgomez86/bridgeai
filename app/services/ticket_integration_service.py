import json
import time
import asyncio
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import quote

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.domain.ticket_integration import TicketResult
from app.repositories.source_connection_repository import SourceConnectionRepository
from app.repositories.ticket_integration_repository import TicketIntegrationRepository
from app.repositories.user_story_repository import UserStoryRepository
from app.services.ticket_providers.azure_devops import AzureDevOpsTicketProvider
from app.services.ticket_providers.base import TicketProvider
from app.services.ticket_providers.jira import JiraTicketProvider  # noqa: F401 (used in health_check)

logger = get_logger(__name__)

_PROVIDERS: dict[str, type[TicketProvider]] = {
    "jira": JiraTicketProvider,
    "azure_devops": AzureDevOpsTicketProvider,
}


class StoryNotFoundError(Exception):
    pass


class UnsupportedProviderError(Exception):
    pass


class ProviderNotConfiguredError(Exception):
    pass


class TicketIntegrationService:
    def __init__(
        self,
        db,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._story_repo = UserStoryRepository(db)
        self._integration_repo = TicketIntegrationRepository(db)
        self._conn_repo = SourceConnectionRepository(db)

    def _resolve_azure_conn(self) -> tuple[str, str, str]:
        """Returns (access_token, org_url, project_name) from the stored connection.

        boards_project is always stored as "{org}/{project_name}".
        For PAT connections base_url holds the org URL directly.
        For OAuth connections base_url is NULL — org URL is derived from boards_project.
        """
        db_conn = (
            self._conn_repo.get_active_for_platform("azure_devops")
            or self._conn_repo.find_by_platform_with_boards_project("azure_devops")
        )
        if not (db_conn and db_conn.access_token and db_conn.boards_project):
            raise ProviderNotConfiguredError(
                "Azure DevOps is not configured. Connect via PAT or OAuth in "
                "Conexiones → Herramientas de gestión and select a project."
            )
        parts = db_conn.boards_project.split("/", 1)
        project_name = parts[-1]
        org_url = db_conn.base_url or ""
        if not org_url and len(parts) == 2:
            org_url = f"https://dev.azure.com/{parts[0]}"
        if not org_url:
            raise ProviderNotConfiguredError(
                "Azure DevOps org URL could not be determined. "
                "Reconnect using PAT with Organization URL."
            )
        return db_conn.access_token, org_url, project_name

    def _refresh_jira_token(self) -> str | None:
        """Refresh the Jira OAuth token and persist it. Returns the new access_token or None on failure."""
        db_conn = self._conn_repo.get_active_for_platform("jira")
        if not (db_conn and db_conn.refresh_token):
            return None
        try:
            from app.services.ticket_providers.jira_oauth import JiraOAuthProvider
            provider = JiraOAuthProvider()
            tokens = provider.refresh_access_token(
                db_conn.refresh_token,
                self._settings.JIRA_CLIENT_ID,
                self._settings.JIRA_CLIENT_SECRET,
            )
            self._conn_repo.update_tokens(
                db_conn.id,
                tokens["access_token"],
                tokens.get("refresh_token") or db_conn.refresh_token,
            )
            logger.info("jira_token_refreshed connection=%s", db_conn.id)
            return tokens["access_token"]
        except Exception as exc:
            logger.warning("jira_token_refresh_failed error=%s", exc)
            return None

    def _get_provider(self, provider_name: str, access_token_override: str | None = None) -> TicketProvider:
        if provider_name not in _PROVIDERS:
            raise UnsupportedProviderError(
                f"Provider '{provider_name}' is not supported. "
                f"Available: {list(_PROVIDERS.keys())}"
            )
        if provider_name == "jira":
            db_conn = self._conn_repo.get_active_for_platform("jira")
            if not (db_conn and db_conn.access_token and db_conn.base_url):
                raise ProviderNotConfiguredError(
                    "Jira is not configured. Connect via OAuth in Conexiones → Herramientas de gestión."
                )
            return JiraTicketProvider(
                self._settings,
                access_token=access_token_override or db_conn.access_token,
                base_url=db_conn.base_url,
                site_url=db_conn.repo_full_name or "",
            )
        if provider_name == "azure_devops":
            access_token, org_url, project_name = self._resolve_azure_conn()
            return AzureDevOpsTicketProvider(
                self._settings,
                access_token=access_token,
                org_url=org_url,
                project=project_name,
            )
        return _PROVIDERS[provider_name](self._settings)

    def _audit(
        self,
        story_id: str,
        provider: str,
        action: str,
        payload: dict | None,
        response: dict | None,
        status: str,
    ) -> None:
        self._integration_repo.add_audit_log(
            story_id=story_id,
            provider=provider,
            action=action,
            payload=json.dumps(payload) if payload else None,
            response=json.dumps(response) if response else None,
            status=status,
            timestamp=datetime.now(timezone.utc),
        )

    def _existing_subtasks(self, story_id: str, provider: str) -> tuple[list[str], list[str], list[str]]:
        log = self._integration_repo.get_latest_subtask_audit(story_id, provider)
        if log and log.response:
            data = json.loads(log.response)
            return data.get("subtask_ids", []), data.get("subtask_urls", []), data.get("subtask_titles", [])
        return [], [], []

    def _duplicate_url(self, provider_name: str, external_ticket_id: str | None) -> str:
        tid = external_ticket_id or ""
        if provider_name == "jira":
            db_conn = self._conn_repo.get_active_for_platform("jira")
            site = db_conn.repo_full_name.rstrip("/") if db_conn and db_conn.repo_full_name else ""
            return f"{site}/browse/{tid}" if site else ""
        if provider_name == "azure_devops" and tid:
            try:
                _, org_url, project_name = self._resolve_azure_conn()
                return f"{org_url}/{quote(project_name)}/_workitems/edit/{tid}"
            except ProviderNotConfiguredError:
                return ""
        return ""

    async def create_ticket(
        self,
        story_id: str,
        provider_name: str,
        project_key: str,
        issue_type: str,
        request_id: str | None = None,
        create_subtasks: bool = True,
    ) -> tuple[TicketResult, bool]:
        """Returns (TicketResult, is_duplicate)."""
        story = self._story_repo.find_domain_by_id(story_id)
        if not story:
            raise StoryNotFoundError(f"UserStory '{story_id}' not found")

        existing = self._integration_repo.find_by_story_and_provider(
            story_id, provider_name
        )
        if existing:
            logger.info(
                "ticket_integration_duplicate",
                extra={
                    "request_id": request_id,
                    "story_id": story_id,
                    "provider": provider_name,
                    "external_ticket_id": existing.external_ticket_id,
                },
            )
            subtask_ids, subtask_urls, subtask_titles = self._existing_subtasks(story_id, provider_name)
            if create_subtasks and not subtask_ids and story.subtasks:
                provider = self._get_provider(provider_name)
                subtask_ids, subtask_urls, subtask_titles, failed = await provider.create_subtasks_for(
                    story, existing.external_ticket_id or "", project_key
                )
                if subtask_ids:
                    self._audit(
                        story_id=story_id,
                        provider=provider_name,
                        action="create_subtasks",
                        payload=None,
                        response={"subtask_ids": subtask_ids, "subtask_urls": subtask_urls, "subtask_titles": subtask_titles, "failed": failed},
                        status="CREATED",
                    )
            return (
                TicketResult(
                    external_id=existing.external_ticket_id or "",
                    url=self._duplicate_url(provider_name, existing.external_ticket_id),
                    provider=provider_name,
                    status="DUPLICATE",
                    subtask_ids=subtask_ids,
                    subtask_urls=subtask_urls,
                    subtask_titles=subtask_titles,
                ),
                True,
            )

        integration_id = self._integration_repo.create_integration(
            story_id=story_id,
            provider=provider_name,
            project_key=project_key,
            issue_type=issue_type,
        )

        provider = self._get_provider(provider_name)
        request_payload = provider.build_payload(story, project_key, issue_type) or {
            "project_key": project_key,
            "issue_type": issue_type,
        }

        start = time.monotonic()
        try:
            try:
                result = await provider.create_ticket(story, project_key, issue_type)
            except HTTPError as exc:
                if exc.code == 401 and provider_name == "jira":
                    new_token = self._refresh_jira_token()
                    if new_token:
                        provider = self._get_provider(provider_name, access_token_override=new_token)
                        result = await provider.create_ticket(story, project_key, issue_type)
                    else:
                        raise
                else:
                    raise

            subtask_ids, subtask_urls, subtask_titles, failed_subtasks = [], [], [], []
            if create_subtasks and story.subtasks:
                subtask_ids, subtask_urls, subtask_titles, failed_subtasks = await provider.create_subtasks_for(
                    story, result.external_id, project_key
                )

            duration_ms = int((time.monotonic() - start) * 1000)

            self._integration_repo.update_status(
                integration_id,
                status="CREATED",
                external_ticket_id=result.external_id,
            )
            self._audit(
                story_id=story_id,
                provider=provider_name,
                action="create_ticket",
                payload=request_payload,
                response={"external_id": result.external_id, "url": result.url, "subtask_ids": subtask_ids, "subtask_urls": subtask_urls, "subtask_titles": subtask_titles},
                status="CREATED",
            )
            logger.info(
                "ticket_integration_success",
                extra={
                    "request_id": request_id,
                    "story_id": story_id,
                    "provider": provider_name,
                    "external_ticket_id": result.external_id,
                    "duration_ms": duration_ms,
                    "retry_count": 0,
                },
            )
            return TicketResult(
                external_id=result.external_id,
                url=result.url,
                provider=result.provider,
                status=result.status,
                subtask_ids=subtask_ids,
                subtask_urls=subtask_urls,
                subtask_titles=subtask_titles,
                failed_subtasks=failed_subtasks,
            ), False

        except HTTPError as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            jira_body = getattr(exc, "jira_error_body", None)
            error_msg = f"HTTP {exc.code}: {exc.reason}"
            if jira_body:
                error_msg = f"{error_msg} — {jira_body}"
            self._integration_repo.update_status(
                integration_id,
                status="FAILED",
                error_message=error_msg[:1000],
            )
            self._audit(
                story_id=story_id,
                provider=provider_name,
                action="create_ticket",
                payload=request_payload,
                response={"error": error_msg, "status_code": exc.code},
                status="FAILED",
            )
            logger.error(
                "ticket_integration_failed",
                extra={
                    "request_id": request_id,
                    "story_id": story_id,
                    "provider": provider_name,
                    "status_code": exc.code,
                    "duration_ms": duration_ms,
                },
            )
            raise

        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            error_msg = str(exc)
            self._integration_repo.update_status(
                integration_id,
                status="FAILED",
                error_message=error_msg,
            )
            self._audit(
                story_id=story_id,
                provider=provider_name,
                action="create_ticket",
                payload=request_payload,
                response={"error": error_msg},
                status="FAILED",
            )
            logger.error(
                "ticket_integration_failed",
                extra={
                    "request_id": request_id,
                    "story_id": story_id,
                    "provider": provider_name,
                    "error": error_msg,
                    "duration_ms": duration_ms,
                },
            )
            raise

    def get_integrations(self, story_id: str) -> list:
        return self._integration_repo.find_all_by_story_id(story_id)

    def get_audit_logs(self, story_id: str) -> list:
        return self._integration_repo.get_audit_logs(story_id)

    async def health_check(self) -> dict[str, str]:
        results: dict[str, str] = {}

        db_jira = self._conn_repo.get_active_for_platform("jira")
        if db_jira and db_jira.access_token and db_jira.base_url:
            try:
                jira = JiraTicketProvider(
                    self._settings,
                    access_token=db_jira.access_token,
                    base_url=db_jira.base_url,
                    site_url=db_jira.repo_full_name or "",
                )
                results["jira"] = "healthy" if await jira.validate_connection() else "unhealthy"
            except Exception:
                results["jira"] = "unhealthy"
        else:
            results["jira"] = "not_configured"

        try:
            access_token, org_url, project_name = self._resolve_azure_conn()
            azure = AzureDevOpsTicketProvider(
                self._settings,
                access_token=access_token,
                org_url=org_url,
                project=project_name,
            )
            results["azure_devops"] = "healthy" if await azure.validate_connection() else "unhealthy"
        except ProviderNotConfiguredError:
            results["azure_devops"] = "not_configured"
        except Exception:
            results["azure_devops"] = "unhealthy"

        return results
