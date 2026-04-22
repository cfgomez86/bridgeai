import json
import time
import asyncio
from datetime import datetime, timezone
from urllib.error import HTTPError

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.domain.ticket_integration import TicketResult
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

    def _get_provider(self, provider_name: str) -> TicketProvider:
        cls = _PROVIDERS.get(provider_name)
        if not cls:
            raise UnsupportedProviderError(
                f"Provider '{provider_name}' is not supported. "
                f"Available: {list(_PROVIDERS.keys())}"
            )
        if provider_name == "jira":
            missing = [k for k, v in {
                "JIRA_BASE_URL": self._settings.JIRA_BASE_URL,
                "JIRA_USER_EMAIL": self._settings.JIRA_USER_EMAIL,
                "JIRA_API_TOKEN": self._settings.JIRA_API_TOKEN,
            }.items() if not v]
            if missing:
                raise ProviderNotConfiguredError(
                    f"Jira is not configured. Missing: {', '.join(missing)}"
                )
        if provider_name == "azure_devops":
            missing = [k for k, v in {
                "AZURE_ORG_URL": self._settings.AZURE_ORG_URL,
                "AZURE_DEVOPS_TOKEN": self._settings.AZURE_DEVOPS_TOKEN,
                "AZURE_PROJECT": self._settings.AZURE_PROJECT,
            }.items() if not v]
            if missing:
                raise ProviderNotConfiguredError(
                    f"Azure DevOps is not configured. Missing: {', '.join(missing)}"
                )
        return cls(self._settings)

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
            return f"{self._settings.JIRA_BASE_URL.rstrip('/')}/browse/{tid}"
        if provider_name == "azure_devops" and tid:
            org = self._settings.AZURE_ORG_URL.rstrip("/")
            return f"{org}/{self._settings.AZURE_PROJECT}/_workitems/edit/{tid}"
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
            result = await provider.create_ticket(story, project_key, issue_type)

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

        if not self._settings.JIRA_BASE_URL or not self._settings.JIRA_API_TOKEN:
            results["jira"] = "not_configured"
        else:
            try:
                jira = JiraTicketProvider(self._settings)
                results["jira"] = "healthy" if await jira.validate_connection() else "unhealthy"
            except Exception:
                results["jira"] = "unhealthy"

        if not self._settings.AZURE_ORG_URL or not self._settings.AZURE_DEVOPS_TOKEN:
            results["azure_devops"] = "not_configured"
        else:
            try:
                azure = AzureDevOpsTicketProvider(self._settings)
                results["azure_devops"] = "healthy" if await azure.validate_connection() else "unhealthy"
            except Exception:
                results["azure_devops"] = "unhealthy"

        return results
