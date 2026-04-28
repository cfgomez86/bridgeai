import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import Settings
from app.domain.user_story import UserStory
from app.services.ticket_providers.jira import JiraTicketProvider


def make_settings(**kwargs) -> Settings:
    defaults = dict(
        DATABASE_URL="sqlite:///:memory:",
        JIRA_REQUEST_TIMEOUT_SECONDS=5,
        JIRA_MAX_RETRIES=2,
        JIRA_RETRY_DELAY_SECONDS=0,
        JIRA_ISSUE_TYPE_MAP="",
    )
    defaults.update(kwargs)
    return Settings(**defaults)


def make_provider(settings: Settings | None = None, **kwargs) -> JiraTicketProvider:
    provider_kwargs = dict(
        access_token="test-oauth-token",
        base_url="https://api.atlassian.com/ex/jira/cloud-id",
        site_url="https://test.atlassian.net",
    )
    provider_kwargs.update(kwargs)
    return JiraTicketProvider(settings or make_settings(), **provider_kwargs)


def make_story(**kwargs) -> UserStory:
    defaults = dict(
        story_id=str(uuid.uuid4()),
        requirement_id="req-1",
        impact_analysis_id="ana-1",
        project_id="proj-1",
        title="User Registration",
        story_description="As a user I want to register",
        acceptance_criteria=["Email is validated", "Password is hashed"],
        subtasks={
            "frontend": [],
            "backend": [
                {"title": "Add endpoint", "description": "Define POST /auth/register and return 201."},
                {"title": "Add repository", "description": "Persist users via the repository pattern."},
            ],
            "configuration": [],
        },
        definition_of_done=["Tests pass", "Code reviewed"],
        risk_notes=["No PII stored in logs"],
        story_points=5,
        risk_level="MEDIUM",
        created_at=datetime.now(timezone.utc),
        generation_time_seconds=1.5,
    )
    defaults.update(kwargs)
    return UserStory(**defaults)



class TestJiraAuth:
    def test_oauth_bearer_header(self):
        provider = make_provider(access_token="my-token")
        assert provider._auth_header() == "Bearer my-token"

    def test_headers_contain_auth_and_json(self):
        provider = make_provider()
        headers = provider._headers()
        assert headers["Authorization"].startswith("Bearer ")
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"


class TestJiraPayloadMapping:
    def test_payload_maps_story_fields(self):
        provider = make_provider()
        story = make_story()
        payload = provider.build_payload(story, "PROJ", "Story")

        fields = payload["fields"]
        assert fields["project"]["key"] == "PROJ"
        assert fields["summary"] == story.title
        assert fields["issuetype"]["name"] == "Story"
        assert "priority" not in fields
        assert "labels" not in fields

    def test_issue_type_map_translates_story_to_historia(self):
        settings = make_settings(JIRA_ISSUE_TYPE_MAP="Story=Historia,Task=Tarea,Bug=Error")
        provider = JiraTicketProvider(settings, access_token="tok", base_url="https://api.atlassian.com/ex/jira/abc")
        payload = provider.build_payload(make_story(), "PROJ", "Story")
        assert payload["fields"]["issuetype"]["name"] == "Historia"

    def test_issue_type_map_is_case_insensitive(self):
        settings = make_settings(JIRA_ISSUE_TYPE_MAP="Story=Historia")
        provider = JiraTicketProvider(settings, access_token="tok", base_url="https://api.atlassian.com/ex/jira/abc")
        payload = provider.build_payload(make_story(), "PROJ", "story")
        assert payload["fields"]["issuetype"]["name"] == "Historia"

    def test_issue_type_unknown_passes_through(self):
        settings = make_settings(JIRA_ISSUE_TYPE_MAP="Story=Historia")
        provider = JiraTicketProvider(settings, access_token="tok", base_url="https://api.atlassian.com/ex/jira/abc")
        payload = provider.build_payload(make_story(), "PROJ", "Epic")
        assert payload["fields"]["issuetype"]["name"] == "Epic"

    def test_description_contains_acceptance_criteria(self):
        provider = make_provider()
        story = make_story()
        payload = provider.build_payload(story, "PROJ", "Story")
        description_json = json.dumps(payload["fields"]["description"])
        assert "Email is validated" in description_json
        assert "Password is hashed" in description_json

    def test_description_does_not_contain_subtasks(self):
        provider = make_provider()
        story = make_story()
        payload = provider.build_payload(story, "PROJ", "Story")
        description_json = json.dumps(payload["fields"]["description"])
        assert "Add endpoint" not in description_json
        assert "Subtareas" not in description_json

    def test_payload_only_contains_required_fields(self):
        provider = make_provider()
        payload = provider.build_payload(make_story(), "PROJ", "Story")
        fields = set(payload["fields"].keys())
        assert fields == {"project", "summary", "description", "issuetype"}


class TestJiraCreateSubtasks:
    async def test_create_subtasks_returns_created_keys(self):
        provider = make_provider()
        subtasks = {
            "frontend": [{"title": "Build form", "description": "React form with email and password."}],
            "backend": [
                {"title": "Add endpoint", "description": "Define POST /auth/register."},
                {"title": "Add repo", "description": "Persist users."},
            ],
            "configuration": [],
        }

        responses = [{"key": "PROJ-2"}, {"key": "PROJ-3"}, {"key": "PROJ-4"}]
        with patch.object(provider, "_request", new=AsyncMock(side_effect=responses)):
            ids, urls, titles, failed = await provider.create_subtasks("PROJ-1", "PROJ", subtasks)

        assert ids == ["PROJ-2", "PROJ-3", "PROJ-4"]
        assert all("PROJ-2" in u or "PROJ-3" in u or "PROJ-4" in u for u in urls)
        assert len(titles) == 3
        assert failed == []

    async def test_create_subtasks_payload_has_parent_and_label(self):
        provider = make_provider()
        payload = provider._build_subtask_payload(
            "PROJ-1", "PROJ", "Add endpoint", "backend",
            "Implement the route.\n\nVerify with pytest.",
        )

        fields = payload["fields"]
        assert fields["parent"]["key"] == "PROJ-1"
        assert fields["issuetype"]["name"] == "Subtask"
        assert fields["labels"] == ["backend"]
        assert fields["summary"] == "[Backend] Add endpoint"

    async def test_create_subtasks_payload_description_has_only_user_paragraphs(self):
        provider = make_provider()
        description = "First step.\n\nSecond step.\n\nVerify with pytest."
        payload = provider._build_subtask_payload(
            "PROJ-1", "PROJ", "Add endpoint", "backend", description,
        )
        adf = payload["fields"]["description"]
        assert adf["type"] == "doc"
        assert len(adf["content"]) == 3
        texts = [p["content"][0]["text"] for p in adf["content"]]
        assert texts == ["First step.", "Second step.", "Verify with pytest."]
        joined = " ".join(texts)
        assert "Parent story:" not in joined
        assert "Risk:" not in joined
        assert "pts" not in joined

    async def test_create_subtasks_payload_truncates_long_summary(self):
        provider = make_provider()
        long_title = "x" * 300
        payload = provider._build_subtask_payload(
            "PROJ-1", "PROJ", long_title, "backend", "Some description here.",
        )
        # "[Backend] " (10 chars) + sliced to 250 total
        assert len(payload["fields"]["summary"]) == 250

    async def test_create_subtasks_payload_uses_config_prefix_for_configuration(self):
        provider = make_provider()
        payload = provider._build_subtask_payload(
            "PROJ-1", "PROJ", "Add env vars", "configuration", "Document SMTP_HOST and SMTP_PORT.",
        )
        assert payload["fields"]["summary"] == "[Config] Add env vars"

    async def test_create_subtasks_payload_uses_frontend_prefix(self):
        provider = make_provider()
        payload = provider._build_subtask_payload(
            "PROJ-1", "PROJ", "Build form", "frontend", "Render inputs and submit handler.",
        )
        assert payload["fields"]["summary"] == "[Frontend] Build form"

    async def test_create_subtasks_skips_failed_items(self):
        from urllib.error import HTTPError

        provider = make_provider()
        subtasks = {
            "frontend": [],
            "backend": [
                {"title": "Task A", "description": "Do something useful here."},
                {"title": "Task B", "description": "Do something else useful here."},
            ],
            "configuration": [],
        }

        error = HTTPError(url="", code=400, msg="Bad Request", hdrs=None, fp=None)
        with patch.object(provider, "_request", new=AsyncMock(side_effect=[error, {"key": "PROJ-2"}])):
            ids, urls, titles, failed = await provider.create_subtasks("PROJ-1", "PROJ", subtasks)

        assert ids == ["PROJ-2"]
        assert len(titles) == 1
        assert failed == ["[Backend] Task A"]


class TestJiraCreateTicket:
    async def test_create_ticket_success(self):
        provider = make_provider()
        story = make_story()

        with patch.object(provider, "_request", new=AsyncMock(return_value={"key": "PROJ-42"})):
            result = await provider.create_ticket(story, "PROJ", "Story")

        assert result.external_id == "PROJ-42"
        assert "PROJ-42" in result.url
        assert result.provider == "jira"
        assert result.status == "CREATED"
        assert result.subtask_ids == []

    async def test_create_ticket_retries_on_5xx(self):
        from urllib.error import HTTPError

        provider = make_provider(settings=make_settings(JIRA_MAX_RETRIES=2, JIRA_RETRY_DELAY_SECONDS=0))
        story = make_story()

        error_500 = HTTPError(url="", code=500, msg="Server Error", hdrs=None, fp=None)

        with patch.object(provider, "create_subtasks", new=AsyncMock(return_value=([], [], []))):
            with patch.object(
                provider, "_request",
                new=AsyncMock(side_effect=[error_500, {"key": "PROJ-1"}]),
            ):
                result = await provider.create_ticket(story, "PROJ", "Story")

        assert result.status == "CREATED"

    async def test_create_ticket_does_not_retry_on_401(self):
        from urllib.error import HTTPError

        provider = make_provider()
        story = make_story()

        error_401 = HTTPError(url="", code=401, msg="Unauthorized", hdrs=None, fp=None)

        with patch.object(provider, "_request", new=AsyncMock(side_effect=error_401)):
            with pytest.raises(HTTPError) as exc_info:
                await provider.create_ticket(story, "PROJ", "Story")

        assert exc_info.value.code == 401

    async def test_create_ticket_raises_after_max_retries(self):
        from urllib.error import HTTPError

        provider = make_provider(settings=make_settings(JIRA_MAX_RETRIES=1, JIRA_RETRY_DELAY_SECONDS=0))
        story = make_story()

        error_503 = HTTPError(url="", code=503, msg="Unavailable", hdrs=None, fp=None)

        with patch.object(provider, "_request", new=AsyncMock(side_effect=error_503)):
            with pytest.raises(HTTPError):
                await provider.create_ticket(story, "PROJ", "Story")


class TestJiraValidateConnection:
    async def test_validate_connection_returns_false_when_not_configured(self):
        provider = make_provider(access_token="", base_url="")
        assert await provider.validate_connection() is False

    async def test_validate_connection_returns_true_on_success(self):
        provider = make_provider()

        with patch.object(provider, "_request", new=AsyncMock(return_value={"accountId": "abc"})):
            assert await provider.validate_connection() is True

    async def test_validate_connection_returns_false_on_error(self):
        from urllib.error import HTTPError

        provider = make_provider()

        with patch.object(
            provider, "_request",
            new=AsyncMock(side_effect=HTTPError(url="", code=401, msg="Unauthorized", hdrs=None, fp=None)),
        ):
            assert await provider.validate_connection() is False
