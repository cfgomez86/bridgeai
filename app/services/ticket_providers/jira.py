import asyncio
import json
import random
from urllib.error import HTTPError

import httpx

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.domain.ticket_integration import TicketResult
from app.domain.user_story import UserStory
from app.services.ticket_providers.base import TicketProvider

logger = get_logger(__name__)

_CATEGORY_PREFIX: dict[str, str] = {
    "frontend": "Frontend",
    "backend": "Backend",
    "configuration": "Config",
}

_ISSUE_TYPE_ALIASES: dict[str, list[str]] = {
    "Story":  ["story", "historia", "user story", "user_story"],
    "Task":   ["task", "tarea"],
    "Bug":    ["bug", "error", "defect"],
    "Epic":   ["epic"],
    "Subtask": ["subtask", "subtarea"],
}


class JiraTicketProvider(TicketProvider):
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        access_token: str = "",
        base_url: str = "",
        site_url: str = "",
    ) -> None:
        self._settings = settings or get_settings()
        self._oauth_token = access_token
        self._oauth_base_url = base_url.rstrip("/") if base_url else ""
        self._site_url = site_url.rstrip("/") if site_url else ""
        self._issue_type_map = self._parse_issue_type_map()
        self._client = httpx.AsyncClient(timeout=self._settings.JIRA_REQUEST_TIMEOUT_SECONDS)

    def _parse_issue_type_map(self) -> dict[str, str]:
        result: dict[str, str] = {}
        raw = self._settings.JIRA_ISSUE_TYPE_MAP.strip()
        if not raw:
            return result
        for pair in raw.split(","):
            pair = pair.strip()
            if "=" not in pair:
                continue
            canonical, jira_name = pair.split("=", 1)
            jira_name = jira_name.strip()
            result[canonical.strip().lower()] = jira_name
            result[jira_name.lower()] = jira_name
        return result

    def _resolve_issue_type(self, issue_type: str) -> str:
        key = issue_type.strip().lower()
        if key in self._issue_type_map:
            return self._issue_type_map[key]
        return issue_type

    def _auth_header(self) -> str:
        return f"Bearer {self._oauth_token}"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self._auth_header(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _api_url(self, path: str) -> str:
        if not self._oauth_base_url:
            raise ValueError("Jira OAuth connection is required but not configured.")
        return f"{self._oauth_base_url}/rest/api/3/{path.lstrip('/')}"

    def _browse_url(self, key: str) -> str:
        return f"{self._site_url}/browse/{key}" if self._site_url else f"/browse/{key}"

    def _build_description_doc(self, story: UserStory) -> dict:
        def section(heading: str, items: list[str]) -> list[dict]:
            if not items:
                return []
            nodes: list[dict] = [
                {
                    "type": "heading",
                    "attrs": {"level": 3},
                    "content": [{"type": "text", "text": heading}],
                }
            ]
            nodes.append({
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": item}],
                            }
                        ],
                    }
                    for item in items
                ],
            })
            return nodes

        content: list[dict] = [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": story.story_description}],
            }
        ]
        content.extend(section("Acceptance Criteria", story.acceptance_criteria))
        content.extend(section("Definition of Done", story.definition_of_done))
        if story.risk_notes:
            content.extend(section("Risk Notes", story.risk_notes))

        return {"type": "doc", "version": 1, "content": content}

    def build_payload(self, story: UserStory, project_key: str, issue_type: str) -> dict:
        resolved_type = self._resolve_issue_type(issue_type)
        return {
            "fields": {
                "project": {"key": project_key},
                "summary": story.title,
                "description": self._build_description_doc(story),
                "issuetype": {"name": resolved_type},
            }
        }

    async def _request(self, method: str, url: str, body: dict | None = None) -> dict:
        response = await self._client.request(
            method, url, json=body, headers=self._headers()
        )
        if response.status_code >= 400:
            error_body = response.text
            logger.error("jira_api_error status=%s body=%s", response.status_code, error_body)
            exc = HTTPError(url, response.status_code, response.reason_phrase, {}, None)  # type: ignore[arg-type]
            exc.jira_error_body = error_body  # type: ignore[attr-defined]
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

    def _build_subtask_payload(
        self,
        parent_key: str,
        project_key: str,
        title: str,
        category: str,
        description: str,
    ) -> dict:
        prefix = _CATEGORY_PREFIX.get(category, category.capitalize())
        summary = f"[{prefix}] {title}"[:250]
        paragraphs = [p.strip() for p in (description or "").split("\n\n") if p.strip()]
        return {
            "fields": {
                "project": {"key": project_key},
                "parent": {"key": parent_key},
                "issuetype": {"name": self._resolve_issue_type("Subtask")},
                "summary": summary,
                "labels": [category],
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": p}]}
                        for p in paragraphs
                    ],
                },
            }
        }

    async def _create_one_subtask(
        self,
        url: str,
        parent_key: str,
        project_key: str,
        title: str,
        category: str,
        description: str,
    ) -> tuple[str | None, str | None, str | None, str | None]:
        """Returns (key, ticket_url, title, error_summary). On success error_summary is None."""
        payload = self._build_subtask_payload(parent_key, project_key, title, category, description)
        prefix = _CATEGORY_PREFIX.get(category, category.capitalize())
        full_title = f"[{prefix}] {title}"[:250]
        max_retries = self._settings.JIRA_MAX_RETRIES
        base_delay = self._settings.JIRA_RETRY_DELAY_SECONDS
        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                response = await self._request("POST", url, payload)
                key = response["key"]
                ticket_url = self._browse_url(key)
                return key, ticket_url, full_title, None
            except HTTPError as exc:
                if exc.code in (400, 401, 403):
                    break
                last_error = exc
                retry_after = (getattr(exc, "headers", None) or {}).get("Retry-After") if exc.code == 429 else None
                logger.warning(
                    "jira_subtask_retryable_error",
                    extra={"parent_key": parent_key, "category": category, "status": exc.code, "attempt": attempt + 1},
                )
            except Exception as exc:
                last_error = exc
                retry_after = None
                logger.warning(
                    "jira_subtask_network_error",
                    extra={"parent_key": parent_key, "category": category, "attempt": attempt + 1},
                )
            if attempt < max_retries:
                wait = self._backoff_seconds(attempt, base_delay, retry_after if isinstance(last_error, HTTPError) and getattr(last_error, "code", None) == 429 else None)
                await asyncio.sleep(wait)

        logger.warning(
            "jira_subtask_creation_failed",
            extra={"parent_key": parent_key, "category": category, "title": title},
        )
        return None, None, None, full_title

    async def create_subtasks(
        self, parent_key: str, project_key: str, subtasks: dict
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        """Create Jira subtasks in parallel. Returns (ids, urls, titles, failed_titles)."""
        url = self._api_url("issue")
        coros = [
            self._create_one_subtask(
                url,
                parent_key,
                project_key,
                item["title"],
                category,
                item.get("description", ""),
            )
            for category, tasks in [
                ("frontend", subtasks.get("frontend") or []),
                ("backend", subtasks.get("backend") or []),
                ("configuration", subtasks.get("configuration") or []),
            ]
            for item in tasks
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
        return await self.create_subtasks(parent_id, project_key, story.subtasks or {})

    async def create_ticket(self, story: UserStory, project_key: str, issue_type: str) -> TicketResult:
        payload = self.build_payload(story, project_key, issue_type)
        url = self._api_url("issue")
        max_retries = self._settings.JIRA_MAX_RETRIES
        base_delay = self._settings.JIRA_RETRY_DELAY_SECONDS
        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                logger.info(
                    "jira_create_ticket_attempt",
                    extra={"story_id": story.story_id, "attempt": attempt + 1},
                )
                response = await self._request("POST", url, payload)
                ticket_id = response["key"]
                ticket_url = self._browse_url(ticket_id)
                return TicketResult(external_id=ticket_id, url=ticket_url, provider="jira", status="CREATED")
            except HTTPError as exc:
                if exc.code in (400, 401, 403):
                    raise
                last_error = exc
                retry_after = (getattr(exc, "headers", None) or {}).get("Retry-After") if exc.code == 429 else None
                logger.warning(
                    "jira_create_ticket_retryable_error",
                    extra={"story_id": story.story_id, "status": exc.code, "attempt": attempt + 1},
                )
            except httpx.RequestError as exc:
                last_error = exc  # type: ignore[assignment]
                retry_after = None
                logger.warning(
                    "jira_create_ticket_network_error",
                    extra={"story_id": story.story_id, "attempt": attempt + 1},
                )

            if attempt < max_retries:
                wait = self._backoff_seconds(attempt, base_delay, retry_after if isinstance(last_error, HTTPError) and last_error.code == 429 else None)
                await asyncio.sleep(wait)

        raise last_error  # type: ignore[misc]

    async def get_ticket(self, external_id: str) -> TicketResult:
        url = self._api_url(f"issue/{external_id}")
        response = await self._request("GET", url)
        ticket_url = self._browse_url(external_id)
        status = response.get("fields", {}).get("status", {}).get("name", "Unknown")
        return TicketResult(external_id=external_id, url=ticket_url, provider="jira", status=status)

    async def validate_connection(self) -> bool:
        if not self._oauth_token or not self._oauth_base_url:
            return False
        try:
            await self._request("GET", self._api_url("myself"))
            return True
        except Exception:
            return False
