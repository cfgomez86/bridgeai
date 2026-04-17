import json
import time
import uuid
import asyncio
from datetime import datetime, timezone
from urllib.error import HTTPError

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.domain.ticket_integration import TicketIntegration, TicketResult
from app.models.ticket_integration import (
    IntegrationAuditLog,
    TicketIntegration as TicketIntegrationModel,
)
from app.models.user_story import UserStory as UserStoryModel
from app.repositories.ticket_integration_repository import TicketIntegrationRepository
from app.repositories.user_story_repository import UserStoryRepository
from app.services.ticket_providers.azure_devops import AzureDevOpsTicketProvider
from app.services.ticket_providers.base import TicketProvider
from app.services.ticket_providers.jira import JiraTicketProvider  # noqa: F401 (used in health_check)
from app.utils.json_utils import parse_json_field

logger = get_logger(__name__)

_PROVIDERS: dict[str, type[TicketProvider]] = {
    "jira": JiraTicketProvider,
    "azure_devops": AzureDevOpsTicketProvider,
}


class StoryNotFoundError(Exception):
    pass


class UnsupportedProviderError(Exception):
    pass


class TicketIntegrationService:
    def __init__(
        self,
        db: Session,
        settings: Settings | None = None,
    ) -> None:
        self._db = db
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
        return cls(self._settings)

    def _story_model_to_domain(self, model: UserStoryModel):
        from app.domain.user_story import UserStory

        return UserStory(
            story_id=model.id,
            requirement_id=model.requirement_id,
            impact_analysis_id=model.impact_analysis_id,
            project_id=model.project_id,
            title=model.title,
            story_description=model.story_description,
            acceptance_criteria=parse_json_field(model.acceptance_criteria),
            technical_tasks=parse_json_field(model.technical_tasks),
            definition_of_done=parse_json_field(model.definition_of_done),
            risk_notes=parse_json_field(model.risk_notes),
            story_points=model.story_points,
            risk_level=model.risk_level,
            created_at=model.created_at,
            generation_time_seconds=model.generation_time_seconds,
        )

    def _audit(
        self,
        story_id: str,
        provider: str,
        action: str,
        payload: dict | None,
        response: dict | None,
        status: str,
    ) -> None:
        log = IntegrationAuditLog(
            id=str(uuid.uuid4()),
            story_id=story_id,
            provider=provider,
            action=action,
            payload=json.dumps(payload) if payload else None,
            response=json.dumps(response) if response else None,
            status=status,
            timestamp=datetime.now(timezone.utc),
        )
        self._integration_repo.add_audit_log(log)

    async def create_ticket(
        self,
        story_id: str,
        provider_name: str,
        project_key: str,
        issue_type: str,
        request_id: str | None = None,
    ) -> tuple[TicketResult, bool]:
        """Returns (TicketResult, is_duplicate)."""
        story_model = self._story_repo.find_by_id(story_id)
        if not story_model:
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
            ticket_url = (
                f"{self._settings.JIRA_BASE_URL.rstrip('/')}/browse/{existing.external_ticket_id}"
                if provider_name == "jira"
                else ""
            )
            return (
                TicketResult(
                    external_id=existing.external_ticket_id or "",
                    url=ticket_url,
                    provider=provider_name,
                    status="DUPLICATE",
                ),
                True,
            )

        now = datetime.now(timezone.utc)
        integration_model = TicketIntegrationModel(
            id=str(uuid.uuid4()),
            story_id=story_id,
            provider=provider_name,
            project_key=project_key,
            issue_type=issue_type,
            external_ticket_id=None,
            status="PENDING",
            retry_count=0,
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        self._integration_repo.save(integration_model)

        story = self._story_model_to_domain(story_model)
        provider = self._get_provider(provider_name)
        request_payload = provider.build_payload(story, project_key, issue_type) or {
            "project_key": project_key,
            "issue_type": issue_type,
        }

        start = time.monotonic()
        try:
            result = await provider.create_ticket(story, project_key, issue_type)
            duration_ms = int((time.monotonic() - start) * 1000)

            self._integration_repo.update_status(
                integration_model.id,
                status="CREATED",
                external_ticket_id=result.external_id,
            )
            self._audit(
                story_id=story_id,
                provider=provider_name,
                action="create_ticket",
                payload=request_payload,
                response={"external_id": result.external_id, "url": result.url},
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
            return result, False

        except HTTPError as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            jira_body = getattr(exc, "jira_error_body", None)
            error_msg = f"HTTP {exc.code}: {exc.reason}"
            if jira_body:
                error_msg = f"{error_msg} — {jira_body}"
            self._integration_repo.update_status(
                integration_model.id,
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
                integration_model.id,
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
