import asyncio
import base64
import random
from urllib.error import HTTPError
from urllib.parse import quote

import httpx

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.domain.ticket_integration import TicketResult
from app.domain.user_story import UserStory
from app.services.ticket_providers.base import TicketProvider

logger = get_logger(__name__)

_API_VERSION = "7.1"

_WORK_ITEM_TYPE_MAP = {
    "story": "User Story",
    "task": "Task",
    "bug": "Bug",
    "epic": "Epic",
}

_PRIORITY_MAP = {
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
}


class AzureDevOpsTicketProvider(TicketProvider):
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _auth_header(self) -> str:
        raw = f":{self._settings.AZURE_DEVOPS_TOKEN}"
        return "Basic " + base64.b64encode(raw.encode()).decode()

    def _headers(self, patch: bool = False) -> dict[str, str]:
        content_type = "application/json-patch+json" if patch else "application/json"
        return {
            "Authorization": self._auth_header(),
            "Content-Type": content_type,
            "Accept": "application/json",
        }

    def _work_items_url(self, work_item_type: str) -> str:
        org = self._settings.AZURE_ORG_URL.rstrip("/")
        project = quote(self._settings.AZURE_PROJECT)
        wtype = quote(work_item_type)
        return f"{org}/{project}/_apis/wit/workitems/${wtype}?api-version={_API_VERSION}"

    def _work_item_url(self, work_item_id: int) -> str:
        org = self._settings.AZURE_ORG_URL.rstrip("/")
        project = quote(self._settings.AZURE_PROJECT)
        return f"{org}/{project}/_apis/wit/workitems/{work_item_id}?api-version={_API_VERSION}"

    def _projects_url(self) -> str:
        org = self._settings.AZURE_ORG_URL.rstrip("/")
        return f"{org}/_apis/projects?api-version={_API_VERSION}"

    def _browse_url(self, work_item_id: int) -> str:
        org = self._settings.AZURE_ORG_URL.rstrip("/")
        project = quote(self._settings.AZURE_PROJECT)
        return f"{org}/{project}/_workitems/edit/{work_item_id}"

    def _build_description_html(self, story: UserStory) -> str:
        def ul(items: list[str]) -> str:
            lis = "".join(f"<li>{item}</li>" for item in items)
            return f"<ul>{lis}</ul>"

        parts = [f"<p>{story.story_description}</p>"]
        if story.acceptance_criteria:
            parts.append("<h3>Acceptance Criteria</h3>")
            parts.append(ul(story.acceptance_criteria))
        subtasks = story.subtasks or {}
        if subtasks.get("frontend"):
            parts.append("<h3>Subtareas Frontend</h3>")
            parts.append(ul(subtasks["frontend"]))
        if subtasks.get("backend"):
            parts.append("<h3>Subtareas Backend</h3>")
            parts.append(ul(subtasks["backend"]))
        if subtasks.get("configuration"):
            parts.append("<h3>Subtareas Configuración</h3>")
            parts.append(ul(subtasks["configuration"]))
        if story.definition_of_done:
            parts.append("<h3>Definition of Done</h3>")
            parts.append(ul(story.definition_of_done))
        if story.risk_notes:
            parts.append("<h3>Risk Notes</h3>")
            parts.append(ul(story.risk_notes))
        return "".join(parts)

    def build_payload(self, story: UserStory, project_key: str, issue_type: str) -> dict:
        priority = _PRIORITY_MAP.get(story.risk_level.upper(), 2)
        ac_text = "\n".join(f"- {item}" for item in story.acceptance_criteria)
        return {
            "work_item_type": _WORK_ITEM_TYPE_MAP.get(issue_type.lower(), issue_type),
            "fields": [
                {"op": "add", "path": "/fields/System.Title", "value": story.title},
                {"op": "add", "path": "/fields/System.Description", "value": self._build_description_html(story)},
                {"op": "add", "path": "/fields/Microsoft.VSTS.Common.AcceptanceCriteria", "value": ac_text},
                {"op": "add", "path": "/fields/Microsoft.VSTS.Common.Priority", "value": priority},
                {"op": "add", "path": "/fields/System.Tags", "value": "BridgeAI; generated"},
                {"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.StoryPoints", "value": story.story_points},
            ],
        }

    async def _request(self, method: str, url: str, body: list | dict | None = None, patch: bool = False) -> dict:
        timeout = self._settings.AZURE_REQUEST_TIMEOUT_SECONDS
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method, url, json=body, headers=self._headers(patch=patch)
            )
        if response.status_code >= 400:
            exc = HTTPError(url, response.status_code, response.reason_phrase, {}, None)  # type: ignore[arg-type]
            raise exc
        return response.json()

    def _backoff_seconds(self, attempt: int, base_delay: int, retry_after: str | None = None) -> float:
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                pass
        cap = base_delay * (2 ** attempt)
        return random.uniform(0, cap)

    async def create_ticket(self, story: UserStory, project_key: str, issue_type: str) -> TicketResult:
        payload_dict = self.build_payload(story, project_key, issue_type)
        work_item_type = payload_dict["work_item_type"]
        fields = payload_dict["fields"]
        url = self._work_items_url(work_item_type)
        max_retries = self._settings.AZURE_MAX_RETRIES
        base_delay = self._settings.AZURE_RETRY_DELAY_SECONDS
        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                logger.info(
                    "azure_create_workitem_attempt",
                    extra={"story_id": story.story_id, "attempt": attempt + 1},
                )
                response = await self._request("POST", url, body=fields, patch=True)
                work_item_id = response["id"]
                return TicketResult(
                    external_id=str(work_item_id),
                    url=self._browse_url(work_item_id),
                    provider="azure_devops",
                    status="CREATED",
                )
            except HTTPError as exc:
                if exc.code in (400, 401, 403):
                    raise
                last_error = exc
                retry_after = (getattr(exc, "headers", None) or {}).get("Retry-After") if exc.code == 429 else None
                logger.warning(
                    "azure_create_workitem_retryable_error",
                    extra={"story_id": story.story_id, "status": exc.code, "attempt": attempt + 1},
                )
            except httpx.RequestError as exc:
                last_error = exc  # type: ignore[assignment]
                retry_after = None
                logger.warning(
                    "azure_create_workitem_network_error",
                    extra={"story_id": story.story_id, "attempt": attempt + 1},
                )

            if attempt < max_retries:
                wait = self._backoff_seconds(attempt, base_delay, retry_after if isinstance(last_error, HTTPError) and last_error.code == 429 else None)
                await asyncio.sleep(wait)

        raise last_error  # type: ignore[misc]

    async def get_ticket(self, external_id: str) -> TicketResult:
        url = self._work_item_url(int(external_id))
        response = await self._request("GET", url)
        state = response.get("fields", {}).get("System.State", "Unknown")
        return TicketResult(
            external_id=external_id,
            url=self._browse_url(int(external_id)),
            provider="azure_devops",
            status=state,
        )

    async def validate_connection(self) -> bool:
        if not self._settings.AZURE_ORG_URL or not self._settings.AZURE_DEVOPS_TOKEN:
            return False
        try:
            await self._request("GET", self._projects_url())
            return True
        except Exception:
            return False
