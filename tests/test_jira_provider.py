import base64
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.domain.user_story import UserStory
from app.services.ticket_providers.jira import JiraTicketProvider


def make_settings(**kwargs) -> Settings:
    defaults = dict(
        DATABASE_URL="sqlite:///:memory:",
        JIRA_BASE_URL="https://test.atlassian.net",
        JIRA_USER_EMAIL="user@test.com",
        JIRA_API_TOKEN="token123",
        JIRA_REQUEST_TIMEOUT_SECONDS=5,
        JIRA_MAX_RETRIES=2,
        JIRA_RETRY_DELAY_SECONDS=0,
        JIRA_ISSUE_TYPE_MAP="",
    )
    defaults.update(kwargs)
    return Settings(**defaults)


def make_story(**kwargs) -> UserStory:
    defaults = dict(
        story_id=str(uuid.uuid4()),
        requirement_id="req-1",
        impact_analysis_id="ana-1",
        project_id="proj-1",
        title="User Registration",
        story_description="As a user I want to register",
        acceptance_criteria=["Email is validated", "Password is hashed"],
        technical_tasks=["Add endpoint", "Add repository"],
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
    def test_basic_auth_header_is_base64_encoded(self):
        settings = make_settings()
        provider = JiraTicketProvider(settings)
        header = provider._auth_header()
        assert header.startswith("Basic ")
        decoded = base64.b64decode(header[6:]).decode()
        assert decoded == "user@test.com:token123"

    def test_headers_contain_auth_and_json(self):
        settings = make_settings()
        provider = JiraTicketProvider(settings)
        headers = provider._headers()
        assert "Authorization" in headers
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"


class TestJiraPayloadMapping:
    def test_payload_maps_story_fields(self):
        settings = make_settings()  # no JIRA_ISSUE_TYPE_MAP → pass-through
        provider = JiraTicketProvider(settings)
        story = make_story()
        payload = provider.build_payload(story, "PROJ", "Story")

        fields = payload["fields"]
        assert fields["project"]["key"] == "PROJ"
        assert fields["summary"] == story.title
        assert fields["issuetype"]["name"] == "Story"
        # priority and labels are omitted to avoid HTTP 400 on restricted screens
        assert "priority" not in fields
        assert "labels" not in fields

    def test_issue_type_map_translates_story_to_historia(self):
        settings = make_settings(JIRA_ISSUE_TYPE_MAP="Story=Historia,Task=Tarea,Bug=Error")
        provider = JiraTicketProvider(settings)
        payload = provider.build_payload(make_story(), "PROJ", "Story")
        assert payload["fields"]["issuetype"]["name"] == "Historia"

    def test_issue_type_map_is_case_insensitive(self):
        settings = make_settings(JIRA_ISSUE_TYPE_MAP="Story=Historia")
        provider = JiraTicketProvider(settings)
        payload = provider.build_payload(make_story(), "PROJ", "story")
        assert payload["fields"]["issuetype"]["name"] == "Historia"

    def test_issue_type_unknown_passes_through(self):
        settings = make_settings(JIRA_ISSUE_TYPE_MAP="Story=Historia")
        provider = JiraTicketProvider(settings)
        payload = provider.build_payload(make_story(), "PROJ", "Epic")
        assert payload["fields"]["issuetype"]["name"] == "Epic"

    def test_description_contains_acceptance_criteria(self):
        settings = make_settings()
        provider = JiraTicketProvider(settings)
        story = make_story()
        payload = provider.build_payload(story, "PROJ", "Story")

        description_json = json.dumps(payload["fields"]["description"])
        assert "Email is validated" in description_json
        assert "Password is hashed" in description_json

    def test_description_contains_technical_tasks(self):
        settings = make_settings()
        provider = JiraTicketProvider(settings)
        story = make_story()
        payload = provider.build_payload(story, "PROJ", "Story")

        description_json = json.dumps(payload["fields"]["description"])
        assert "Add endpoint" in description_json

    def test_payload_only_contains_required_fields(self):
        settings = make_settings()
        provider = JiraTicketProvider(settings)
        payload = provider.build_payload(make_story(), "PROJ", "Story")
        fields = set(payload["fields"].keys())
        # Only required fields — optional ones cause 400 on restricted project screens
        assert fields == {"project", "summary", "description", "issuetype"}


class TestJiraCreateTicket:
    def test_create_ticket_success(self):
        settings = make_settings()
        provider = JiraTicketProvider(settings)
        story = make_story()

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"key": "PROJ-42"}).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("app.services.ticket_providers.jira.urlopen", return_value=mock_response):
            result = provider.create_ticket(story, "PROJ", "Story")

        assert result.external_id == "PROJ-42"
        assert "PROJ-42" in result.url
        assert result.provider == "jira"
        assert result.status == "CREATED"

    def test_create_ticket_retries_on_5xx(self):
        from urllib.error import HTTPError

        settings = make_settings(JIRA_MAX_RETRIES=2, JIRA_RETRY_DELAY_SECONDS=0)
        provider = JiraTicketProvider(settings)
        story = make_story()

        error_500 = HTTPError(url="", code=500, msg="Server Error", hdrs=None, fp=None)
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"key": "PROJ-1"}).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch(
            "app.services.ticket_providers.jira.urlopen",
            side_effect=[error_500, mock_response],
        ):
            result = provider.create_ticket(story, "PROJ", "Story")

        assert result.status == "CREATED"

    def test_create_ticket_does_not_retry_on_401(self):
        from urllib.error import HTTPError

        settings = make_settings()
        provider = JiraTicketProvider(settings)
        story = make_story()

        error_401 = HTTPError(url="", code=401, msg="Unauthorized", hdrs=None, fp=None)

        with patch("app.services.ticket_providers.jira.urlopen", side_effect=error_401):
            with pytest.raises(HTTPError) as exc_info:
                provider.create_ticket(story, "PROJ", "Story")

        assert exc_info.value.code == 401

    def test_create_ticket_raises_after_max_retries(self):
        from urllib.error import HTTPError

        settings = make_settings(JIRA_MAX_RETRIES=1, JIRA_RETRY_DELAY_SECONDS=0)
        provider = JiraTicketProvider(settings)
        story = make_story()

        error_503 = HTTPError(url="", code=503, msg="Unavailable", hdrs=None, fp=None)

        with patch("app.services.ticket_providers.jira.urlopen", side_effect=error_503):
            with pytest.raises(HTTPError):
                provider.create_ticket(story, "PROJ", "Story")


class TestJiraValidateConnection:
    def test_validate_connection_returns_false_when_not_configured(self):
        settings = make_settings(JIRA_BASE_URL="", JIRA_API_TOKEN="")
        provider = JiraTicketProvider(settings)
        assert provider.validate_connection() is False

    def test_validate_connection_returns_true_on_success(self):
        settings = make_settings()
        provider = JiraTicketProvider(settings)

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"accountId": "abc"}).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("app.services.ticket_providers.jira.urlopen", return_value=mock_response):
            assert provider.validate_connection() is True

    def test_validate_connection_returns_false_on_error(self):
        from urllib.error import HTTPError

        settings = make_settings()
        provider = JiraTicketProvider(settings)

        with patch(
            "app.services.ticket_providers.jira.urlopen",
            side_effect=HTTPError(url="", code=401, msg="Unauthorized", hdrs=None, fp=None),
        ):
            assert provider.validate_connection() is False
