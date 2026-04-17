import asyncio
import base64
import json
import random
from urllib.error import HTTPError
from urllib.parse import urljoin

import httpx

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.domain.ticket_integration import TicketResult
from app.domain.user_story import UserStory
from app.services.ticket_providers.base import TicketProvider

logger = get_logger(__name__)

_ISSUE_TYPE_ALIASES: dict[str, list[str]] = {
    "Story":  ["story", "historia", "user story", "user_story"],
    "Task":   ["task", "tarea"],
    "Bug":    ["bug", "error", "defect"],
    "Epic":   ["epic"],
    "Subtask": ["subtask", "subtarea"],
}


class JiraTicketProvider(TicketProvider):
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._issue_type_map = self._parse_issue_type_map()

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
        raw = f"{self._settings.JIRA_USER_EMAIL}:{self._settings.JIRA_API_TOKEN}"
        return "Basic " + base64.b64encode(raw.encode()).decode()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self._auth_header(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _api_url(self, path: str) -> str:
        base = self._settings.JIRA_BASE_URL.rstrip("/")
        return f"{base}/rest/api/3/{path.lstrip('/')}"

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
        content.extend(section("Technical Tasks", story.technical_tasks))
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
        timeout = self._settings.JIRA_REQUEST_TIMEOUT_SECONDS
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
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
                ticket_url = urljoin(self._settings.JIRA_BASE_URL, f"/browse/{ticket_id}")
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
        ticket_url = urljoin(self._settings.JIRA_BASE_URL, f"/browse/{external_id}")
        status = response.get("fields", {}).get("status", {}).get("name", "Unknown")
        return TicketResult(external_id=external_id, url=ticket_url, provider="jira", status=status)

    async def validate_connection(self) -> bool:
        if not self._settings.JIRA_BASE_URL or not self._settings.JIRA_API_TOKEN:
            return False
        try:
            await self._request("GET", self._api_url("myself"))
            return True
        except Exception:
            return False
