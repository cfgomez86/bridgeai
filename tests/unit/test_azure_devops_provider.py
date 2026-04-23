import base64
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.domain.user_story import UserStory
from app.services.ticket_providers.azure_devops import AzureDevOpsTicketProvider


def make_settings(**kwargs) -> Settings:
    defaults = dict(
        DATABASE_URL="sqlite:///:memory:",
        AZURE_ORG_URL="https://dev.azure.com/test-org",
        AZURE_DEVOPS_TOKEN="pat-token-123",
        AZURE_PROJECT="MyProject",
        AZURE_REQUEST_TIMEOUT_SECONDS=5,
        AZURE_MAX_RETRIES=2,
        AZURE_RETRY_DELAY_SECONDS=0,
    )
    defaults.update(kwargs)
    return Settings(**defaults)


def make_story(**kwargs) -> UserStory:
    defaults = dict(
        story_id=str(uuid.uuid4()),
        requirement_id="req-1",
        impact_analysis_id="ana-1",
        project_id="proj-1",
        title="User Registration with Email",
        story_description="As a user I want to register",
        acceptance_criteria=["Email is validated", "Password min 8 chars"],
        subtasks={"frontend": [], "backend": ["Add endpoint", "Add repository"], "configuration": []},
        definition_of_done=["Tests pass", "Code reviewed"],
        risk_notes=["No PII in logs"],
        story_points=5,
        risk_level="MEDIUM",
        created_at=datetime.now(timezone.utc),
        generation_time_seconds=1.5,
    )
    defaults.update(kwargs)
    return UserStory(**defaults)


class TestAzureAuth:
    def test_pat_auth_header_uses_base64_colon_token(self):
        settings = make_settings()
        provider = AzureDevOpsTicketProvider(settings)
        header = provider._auth_header()

        assert header.startswith("Basic ")
        decoded = base64.b64decode(header[6:]).decode()
        assert decoded == ":pat-token-123"

    def test_patch_request_uses_json_patch_content_type(self):
        settings = make_settings()
        provider = AzureDevOpsTicketProvider(settings)
        headers = provider._headers(patch=True)
        assert headers["Content-Type"] == "application/json-patch+json"

    def test_regular_request_uses_json_content_type(self):
        settings = make_settings()
        provider = AzureDevOpsTicketProvider(settings)
        headers = provider._headers(patch=False)
        assert headers["Content-Type"] == "application/json"


class TestAzurePayloadMapping:
    def test_payload_maps_title(self):
        settings = make_settings()
        provider = AzureDevOpsTicketProvider(settings)
        story = make_story()
        payload = provider.build_payload(story, "PROJ", "Story")

        title_op = next(
            f for f in payload["fields"] if f["path"] == "/fields/System.Title"
        )
        assert title_op["value"] == story.title

    def test_payload_maps_work_item_type_story(self):
        settings = make_settings()
        provider = AzureDevOpsTicketProvider(settings)
        payload = provider.build_payload(make_story(), "PROJ", "Story")
        assert payload["work_item_type"] == "User Story"

    def test_payload_maps_work_item_type_bug(self):
        settings = make_settings()
        provider = AzureDevOpsTicketProvider(settings)
        payload = provider.build_payload(make_story(), "PROJ", "Bug")
        assert payload["work_item_type"] == "Bug"

    def test_payload_maps_acceptance_criteria(self):
        settings = make_settings()
        provider = AzureDevOpsTicketProvider(settings)
        story = make_story()
        payload = provider.build_payload(story, "PROJ", "Story")

        ac_op = next(
            f for f in payload["fields"]
            if f["path"] == "/fields/Microsoft.VSTS.Common.AcceptanceCriteria"
        )
        assert "Email is validated" in ac_op["value"]
        assert "Password min 8 chars" in ac_op["value"]

    def test_payload_description_contains_all_sections(self):
        settings = make_settings()
        provider = AzureDevOpsTicketProvider(settings)
        story = make_story()
        payload = provider.build_payload(story, "PROJ", "Story")

        desc_op = next(
            f for f in payload["fields"]
            if f["path"] == "/fields/System.Description"
        )
        html = desc_op["value"]
        assert "As a user I want to register" in html
        assert "Acceptance Criteria" in html
        assert "Subtareas Backend" not in html
        assert "Definition of Done" in html
        assert "Risk Notes" in html

    def test_priority_maps_high_to_1(self):
        settings = make_settings()
        provider = AzureDevOpsTicketProvider(settings)
        payload = provider.build_payload(make_story(risk_level="HIGH"), "PROJ", "Story")
        prio_op = next(
            f for f in payload["fields"]
            if f["path"] == "/fields/Microsoft.VSTS.Common.Priority"
        )
        assert prio_op["value"] == 1

    def test_story_points_mapped(self):
        settings = make_settings()
        provider = AzureDevOpsTicketProvider(settings)
        payload = provider.build_payload(make_story(story_points=8), "PROJ", "Story")
        sp_op = next(
            f for f in payload["fields"]
            if f["path"] == "/fields/Microsoft.VSTS.Scheduling.StoryPoints"
        )
        assert sp_op["value"] == 8

    def test_tags_include_bridgeai(self):
        settings = make_settings()
        provider = AzureDevOpsTicketProvider(settings)
        payload = provider.build_payload(make_story(), "PROJ", "Story")
        tags_op = next(
            f for f in payload["fields"]
            if f["path"] == "/fields/System.Tags"
        )
        assert "BridgeAI" in tags_op["value"]


class TestAzureCreateChildTasks:
    async def test_create_child_tasks_returns_ids(self):
        settings = make_settings()
        provider = AzureDevOpsTicketProvider(settings)
        subtasks = {"frontend": ["Build form"], "backend": ["Add endpoint", "Add repo"], "configuration": []}

        responses = [{"id": 101}, {"id": 102}, {"id": 103}]
        with patch.object(provider, "_request", new=AsyncMock(side_effect=responses)):
            ids, urls, titles, failed = await provider.create_child_tasks(42, subtasks)

        assert ids == ["101", "102", "103"]
        assert all("101" in u or "102" in u or "103" in u for u in urls)
        assert len(titles) == 3
        assert failed == []

    def test_child_task_payload_has_parent_relation(self):
        settings = make_settings()
        provider = AzureDevOpsTicketProvider(settings)
        payload = provider._build_child_task_payload(42, "Add endpoint", "backend")

        relation_op = next(op for op in payload if op["path"] == "/relations/-")
        assert relation_op["value"]["rel"] == "System.LinkTypes.Hierarchy-Reverse"
        assert "42" in relation_op["value"]["url"]

        title_op = next(op for op in payload if op["path"] == "/fields/System.Title")
        assert title_op["value"] == "[Backend] Add endpoint"

        tags_op = next(op for op in payload if op["path"] == "/fields/System.Tags")
        assert "backend" in tags_op["value"]

    def test_child_task_payload_uses_config_prefix_for_configuration(self):
        settings = make_settings()
        provider = AzureDevOpsTicketProvider(settings)
        payload = provider._build_child_task_payload(42, "Add env vars", "configuration")
        title_op = next(op for op in payload if op["path"] == "/fields/System.Title")
        assert title_op["value"] == "[Config] Add env vars"

    def test_child_task_payload_uses_frontend_prefix(self):
        settings = make_settings()
        provider = AzureDevOpsTicketProvider(settings)
        payload = provider._build_child_task_payload(42, "Build form", "frontend")
        title_op = next(op for op in payload if op["path"] == "/fields/System.Title")
        assert title_op["value"] == "[Frontend] Build form"

    async def test_create_child_tasks_skips_failed_items(self):
        from urllib.error import HTTPError

        settings = make_settings()
        provider = AzureDevOpsTicketProvider(settings)
        subtasks = {"frontend": [], "backend": ["Task A", "Task B"], "configuration": []}

        error = HTTPError(url="", code=400, msg="Bad Request", hdrs=None, fp=None)
        with patch.object(provider, "_request", new=AsyncMock(side_effect=[error, {"id": 55}])):
            ids, urls, titles, failed = await provider.create_child_tasks(10, subtasks)

        assert ids == ["55"]
        assert len(titles) == 1
        assert failed == ["Task A"]


class TestAzureCreateTicket:
    async def test_create_ticket_success(self):
        settings = make_settings()
        provider = AzureDevOpsTicketProvider(settings)
        story = make_story()

        with patch.object(provider, "_request", new=AsyncMock(return_value={"id": 42})):
            result = await provider.create_ticket(story, "PROJ", "Story")

        assert result.external_id == "42"
        assert "42" in result.url
        assert result.provider == "azure_devops"
        assert result.status == "CREATED"
        assert result.subtask_ids == []

    async def test_create_ticket_url_contains_org_and_project(self):
        settings = make_settings()
        provider = AzureDevOpsTicketProvider(settings)
        story = make_story()

        with patch.object(provider, "create_child_tasks", new=AsyncMock(return_value=([], [], []))):
            with patch.object(provider, "_request", new=AsyncMock(return_value={"id": 7})):
                result = await provider.create_ticket(story, "PROJ", "Story")

        assert "test-org" in result.url
        assert "MyProject" in result.url

    async def test_create_ticket_retries_on_5xx(self):
        from urllib.error import HTTPError

        settings = make_settings(AZURE_MAX_RETRIES=2, AZURE_RETRY_DELAY_SECONDS=0)
        provider = AzureDevOpsTicketProvider(settings)
        story = make_story()

        error_503 = HTTPError(url="", code=503, msg="Unavailable", hdrs=None, fp=None)
        with patch.object(provider, "create_child_tasks", new=AsyncMock(return_value=([], [], []))):
            with patch.object(provider, "_request", new=AsyncMock(side_effect=[error_503, {"id": 5}])):
                result = await provider.create_ticket(story, "PROJ", "Story")

        assert result.status == "CREATED"

    async def test_create_ticket_does_not_retry_on_401(self):
        from urllib.error import HTTPError

        settings = make_settings()
        provider = AzureDevOpsTicketProvider(settings)
        story = make_story()

        error_401 = HTTPError(url="", code=401, msg="Unauthorized", hdrs=None, fp=None)
        with patch.object(provider, "_request", new=AsyncMock(side_effect=error_401)):
            with pytest.raises(HTTPError) as exc_info:
                await provider.create_ticket(story, "PROJ", "Story")

        assert exc_info.value.code == 401

    async def test_create_ticket_raises_after_max_retries(self):
        from urllib.error import HTTPError

        settings = make_settings(AZURE_MAX_RETRIES=1, AZURE_RETRY_DELAY_SECONDS=0)
        provider = AzureDevOpsTicketProvider(settings)
        story = make_story()

        error_500 = HTTPError(url="", code=500, msg="Error", hdrs=None, fp=None)
        with patch.object(provider, "_request", new=AsyncMock(side_effect=error_500)):
            with pytest.raises(HTTPError):
                await provider.create_ticket(story, "PROJ", "Story")

    async def test_429_triggers_retry_with_jitter(self):
        from urllib.error import HTTPError

        settings = make_settings(AZURE_MAX_RETRIES=2, AZURE_RETRY_DELAY_SECONDS=0)
        provider = AzureDevOpsTicketProvider(settings)
        story = make_story()

        error_429 = HTTPError(url="", code=429, msg="Too Many Requests", hdrs=None, fp=None)
        with patch.object(provider, "create_child_tasks", new=AsyncMock(return_value=([], [], []))):
            with patch.object(provider, "_request", new=AsyncMock(side_effect=[error_429, {"id": 99}])):
                result = await provider.create_ticket(story, "PROJ", "Story")

        assert result.status == "CREATED"


class TestAzureValidateConnection:
    async def test_returns_false_when_not_configured(self):
        settings = make_settings(AZURE_ORG_URL="", AZURE_DEVOPS_TOKEN="")
        provider = AzureDevOpsTicketProvider(settings)
        assert await provider.validate_connection() is False

    async def test_returns_true_on_success(self):
        settings = make_settings()
        provider = AzureDevOpsTicketProvider(settings)

        with patch.object(provider, "_request", new=AsyncMock(return_value={"value": []})):
            assert await provider.validate_connection() is True

    async def test_returns_false_on_error(self):
        from urllib.error import HTTPError

        settings = make_settings()
        provider = AzureDevOpsTicketProvider(settings)

        with patch.object(
            provider, "_request",
            new=AsyncMock(side_effect=HTTPError(url="", code=401, msg="Unauthorized", hdrs=None, fp=None)),
        ):
            assert await provider.validate_connection() is False


class TestHealthCheckWithAzure:
    async def test_health_shows_azure_not_configured(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from app.database.session import Base
        from app.services.ticket_integration_service import TicketIntegrationService

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        db = sessionmaker(bind=engine)()

        settings = make_settings(
            AZURE_ORG_URL="", AZURE_DEVOPS_TOKEN="",
        )
        service = TicketIntegrationService(db, settings)
        result = await service.health_check()

        assert result["jira"] == "not_configured"
        assert result["azure_devops"] == "not_configured"

    async def test_health_shows_azure_healthy(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from app.database.session import Base
        from app.services.ticket_integration_service import TicketIntegrationService

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        db = sessionmaker(bind=engine)()

        settings = make_settings()
        service = TicketIntegrationService(db, settings)

        with patch(
            "app.services.ticket_providers.azure_devops.AzureDevOpsTicketProvider._request",
            new_callable=AsyncMock,
            return_value={"value": []},
        ):
            result = await service.health_check()

        assert result["azure_devops"] == "healthy"
