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

_CATEGORY_PREFIX: dict[str, str] = {
    "frontend": "Frontend",
    "backend": "Backend",
    "configuration": "Config",
}

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
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        access_token: str = "",
        org_url: str = "",
        project: str = "",
    ) -> None:
        self._settings = settings or get_settings()
        self._access_token = access_token
        self._org_url = org_url.rstrip("/") if org_url else ""
        self._project = project
        self._client = httpx.AsyncClient(timeout=self._settings.AZURE_REQUEST_TIMEOUT_SECONDS)

    @property
    def _eff_org(self) -> str:
        return self._org_url or self._settings.AZURE_ORG_URL.rstrip("/")

    @property
    def _eff_project(self) -> str:
        return self._project or self._settings.AZURE_PROJECT

    def _auth_header(self) -> str:
        # Entra ID access tokens are JWTs (always start with "eyJ") — use Bearer auth
        # Azure DevOps PATs are opaque strings — use HTTP Basic Auth
        token = self._access_token or self._settings.AZURE_DEVOPS_TOKEN
        if token.startswith("eyJ"):
            return f"Bearer {token}"
        return "Basic " + base64.b64encode(f":{token}".encode()).decode()

    def _headers(self, patch: bool = False) -> dict[str, str]:
        content_type = "application/json-patch+json" if patch else "application/json"
        return {
            "Authorization": self._auth_header(),
            "Content-Type": content_type,
            "Accept": "application/json",
        }

    def _work_items_url(self, work_item_type: str) -> str:
        wtype = quote(work_item_type)
        return f"{self._eff_org}/{quote(self._eff_project)}/_apis/wit/workitems/${wtype}?api-version={_API_VERSION}"

    def _work_item_url(self, work_item_id: int) -> str:
        return f"{self._eff_org}/{quote(self._eff_project)}/_apis/wit/workitems/{work_item_id}?api-version={_API_VERSION}"

    def _projects_url(self) -> str:
        return f"{self._eff_org}/_apis/projects?api-version={_API_VERSION}"

    def _work_item_relation_url(self, work_item_id: int) -> str:
        return f"{self._eff_org}/{quote(self._eff_project)}/_apis/wit/workitems/{work_item_id}"

    def _browse_url(self, work_item_id: int) -> str:
        return f"{self._eff_org}/{quote(self._eff_project)}/_workitems/edit/{work_item_id}"

    def _build_description_html(self, story: UserStory) -> str:
        def ul(items: list[str]) -> str:
            lis = "".join(f"<li>{item}</li>" for item in items)
            return f"<ul>{lis}</ul>"

        parts = [f"<p>{story.story_description}</p>"]
        if story.acceptance_criteria:
            parts.append("<h3>Acceptance Criteria</h3>")
            parts.append(ul(story.acceptance_criteria))
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
        response = await self._client.request(
            method, url, json=body, headers=self._headers(patch=patch)
        )
        if response.status_code >= 400:
            if response.status_code == 401:
                raise HTTPError(  # type: ignore[arg-type]
                    url, 401,
                    "Unauthorized — verify your Azure DevOps PAT includes 'Work Items: Read & Write' scope",
                    {}, None,
                )
            if response.status_code == 404:
                raise HTTPError(  # type: ignore[arg-type]
                    url, 404,
                    "Not Found — verify the project name and work item type. "
                    "Azure DevOps work item types depend on the project's process template: "
                    "Agile → 'User Story', Scrum → 'Product Backlog Item', Basic → 'Issue'. "
                    "'Task' and 'Bug' are available in most templates.",
                    {}, None,
                )
            raise HTTPError(url, response.status_code, response.reason_phrase, {}, None)  # type: ignore[arg-type]
        return response.json()

    def _backoff_seconds(self, attempt: int, base_delay: int, retry_after: str | None = None) -> float:
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                pass
        cap = base_delay * (2 ** attempt)
        return random.uniform(0, cap)

    def _build_child_task_payload(self, parent_id: int, summary: str, category: str, description: str = "") -> list:
        ops = [
            {"op": "add", "path": "/fields/System.Title", "value": f"[{_CATEGORY_PREFIX.get(category, category.capitalize())}] {summary}"},
            {"op": "add", "path": "/fields/System.Tags", "value": f"BridgeAI; {category}"},
            {"op": "add", "path": "/relations/-", "value": {
                "rel": "System.LinkTypes.Hierarchy-Reverse",
                "url": self._work_item_relation_url(parent_id),
                "attributes": {"comment": "BridgeAI generated task"},
            }},
        ]
        if description:
            ops.insert(1, {"op": "add", "path": "/fields/System.Description", "value": f"<p>{description}</p>"})
        return ops

    async def _create_one_child_task(
        self, url: str, parent_id: int, summary: str, category: str, description: str = ""
    ) -> tuple[str | None, str | None, str | None, str | None]:
        """Returns (id, browse_url, title, error_summary). On success error_summary is None."""
        payload = self._build_child_task_payload(parent_id, summary, category, description)
        full_title = f"[{_CATEGORY_PREFIX.get(category, category.capitalize())}] {summary}"
        max_retries = self._settings.AZURE_MAX_RETRIES
        base_delay = self._settings.AZURE_RETRY_DELAY_SECONDS
        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                response = await self._request("POST", url, body=payload, patch=True)
                work_item_id = response["id"]
                return str(work_item_id), self._browse_url(work_item_id), full_title, None
            except HTTPError as exc:
                if exc.code in (400, 401, 403, 404):
                    break
                last_error = exc
                retry_after = (getattr(exc, "headers", None) or {}).get("Retry-After") if exc.code == 429 else None
                logger.warning(
                    "azure_child_task_retryable_error",
                    extra={"parent_id": parent_id, "category": category, "status": exc.code, "attempt": attempt + 1},
                )
            except Exception as exc:
                last_error = exc
                retry_after = None
                logger.warning(
                    "azure_child_task_network_error",
                    extra={"parent_id": parent_id, "category": category, "attempt": attempt + 1},
                )
            if attempt < max_retries:
                wait = self._backoff_seconds(attempt, base_delay, retry_after if isinstance(last_error, HTTPError) and getattr(last_error, "code", None) == 429 else None)
                await asyncio.sleep(wait)

        logger.warning(
            "azure_child_task_creation_failed",
            extra={"parent_id": parent_id, "category": category, "summary": summary},
        )
        return None, None, None, summary

    async def create_child_tasks(
        self, parent_id: int, subtasks: dict, description: str = ""
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        """Create Azure Repos Tasks in parallel. Returns (ids, urls, titles, failed_summaries)."""
        url = self._work_items_url("Task")
        coros = [
            self._create_one_child_task(url, parent_id, summary, category, description)
            for category, tasks in [
                ("frontend", subtasks.get("frontend") or []),
                ("backend", subtasks.get("backend") or []),
                ("configuration", subtasks.get("configuration") or []),
            ]
            for summary in tasks
        ]
        results = await asyncio.gather(*coros)
        ids = [r[0] for r in results if r[0] is not None]
        urls = [r[1] for r in results if r[1] is not None]
        titles = [r[2] for r in results if r[2] is not None]
        failed = [r[3] for r in results if r[3] is not None]
        return ids, urls, titles, failed

    async def create_subtasks_for(
        self, story: UserStory, parent_id: str, project_key: str
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        description = f"Parent story: {story.title} | Risk: {story.risk_level} | {story.story_points} pts"
        return await self.create_child_tasks(int(parent_id), story.subtasks or {}, description)

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
                if exc.code in (400, 401, 403, 404):
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
        if not self._eff_org or not (self._access_token or self._settings.AZURE_DEVOPS_TOKEN):
            return False
        try:
            await self._request("GET", self._projects_url())
            return True
        except Exception:
            return False
