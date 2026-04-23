import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.database.session import Base, get_db
from app.domain.ticket_integration import TicketResult
from app.main import create_app
from tests.integration.auth_helpers import apply_mock_auth, TEST_TENANT_ID
from app.models.user_story import UserStory as UserStoryModel
from app.api.routes.ticket_integration import get_integration_service
from app.services.ticket_integration_service import TicketIntegrationService


def make_settings(**kwargs) -> Settings:
    defaults = dict(
        DATABASE_URL="sqlite:///:memory:",
        JIRA_BASE_URL="https://test.atlassian.net",
        JIRA_USER_EMAIL="user@test.com",
        JIRA_API_TOKEN="token123",
        JIRA_MAX_RETRIES=1,
        JIRA_RETRY_DELAY_SECONDS=0,
    )
    defaults.update(kwargs)
    return Settings(**defaults)


def make_client_with_story(story_id: str = "story-endpoint-1"):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    from tests.integration.auth_helpers import TEST_CONNECTION_ID
    story = UserStoryModel(
        id=story_id,
        tenant_id=TEST_TENANT_ID,
        source_connection_id=TEST_CONNECTION_ID,
        requirement_id="req-1",
        impact_analysis_id="ana-1",
        project_id="proj-1",
        title="Test Story",
        story_description="As a user...",
        acceptance_criteria=json.dumps(["AC1"]),
        subtasks=json.dumps({"frontend": [], "backend": ["Task1"], "configuration": []}),
        definition_of_done=json.dumps(["DoD1"]),
        risk_notes=json.dumps([]),
        story_points=5,
        risk_level="MEDIUM",
        generation_time_seconds=1.0,
        created_at=datetime.now(timezone.utc),
    )
    db.add(story)
    db.commit()

    settings = make_settings()
    app = apply_mock_auth(create_app())

    def override_db():
        yield db

    def override_service():
        return TicketIntegrationService(db=db, settings=settings)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_integration_service] = override_service

    return TestClient(app), db


class TestCreateTicketEndpoint:
    def test_returns_201_on_success(self):
        client, db = make_client_with_story("story-1")
        mock_result = TicketResult(
            external_id="PROJ-10",
            url="https://test.atlassian.net/browse/PROJ-10",
            provider="jira",
            status="CREATED",
        )

        with patch(
            "app.services.ticket_integration_service.TicketIntegrationService._get_provider"
        ) as mock_factory:
            mock_provider = MagicMock()
            mock_provider.create_ticket = AsyncMock(return_value=mock_result)
            mock_provider.create_subtasks_for = AsyncMock(return_value=([], [], [], []))
            mock_provider.build_payload.return_value = {"fields": {"summary": "Test Story"}}
            mock_factory.return_value = mock_provider

            response = client.post("/api/v1/tickets", json={
                "story_id": "story-1",
                "integration_type": "jira",
                "project_key": "PROJ",
                "issue_type": "Story",
            })

        assert response.status_code == 201
        data = response.json()
        assert data["ticket_id"] == "PROJ-10"
        assert data["provider"] == "jira"
        assert data["status"] == "CREATED"

    def test_returns_404_for_nonexistent_story(self):
        client, _ = make_client_with_story()
        response = client.post("/api/v1/tickets", json={
            "story_id": "nonexistent-id",
            "integration_type": "jira",
            "project_key": "PROJ",
            "issue_type": "Story",
        })
        assert response.status_code == 404

    def test_returns_400_for_unsupported_provider(self):
        client, _ = make_client_with_story("story-unsupported")
        response = client.post("/api/v1/tickets", json={
            "story_id": "story-unsupported",
            "integration_type": "servicenow",
            "project_key": "PROJ",
            "issue_type": "Story",
        })
        assert response.status_code == 400

    def test_returns_200_on_duplicate(self):
        client, db = make_client_with_story("story-dup")
        mock_result = TicketResult(
            external_id="PROJ-5",
            url="https://test.atlassian.net/browse/PROJ-5",
            provider="jira",
            status="CREATED",
        )

        with patch(
            "app.services.ticket_integration_service.TicketIntegrationService._get_provider"
        ) as mock_factory:
            mock_provider = MagicMock()
            mock_provider.create_ticket = AsyncMock(return_value=mock_result)
            mock_provider.create_subtasks_for = AsyncMock(return_value=([], [], [], []))
            mock_provider.build_payload.return_value = {"fields": {"summary": "Dup Story"}}
            mock_factory.return_value = mock_provider

            # First call
            client.post("/api/v1/tickets", json={
                "story_id": "story-dup",
                "integration_type": "jira",
                "project_key": "PROJ",
                "issue_type": "Story",
            })
            # Second call
            response = client.post("/api/v1/tickets", json={
                "story_id": "story-dup",
                "integration_type": "jira",
                "project_key": "PROJ",
                "issue_type": "Story",
            })

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Ticket already exists"

    def test_azure_devops_creates_ticket(self):
        from app.domain.ticket_integration import TicketResult

        client, db = make_client_with_story("story-azure")
        mock_result = TicketResult(
            external_id="42",
            url="https://dev.azure.com/org/proj/_workitems/edit/42",
            provider="azure_devops",
            status="CREATED",
        )

        with patch(
            "app.services.ticket_integration_service.TicketIntegrationService._get_provider"
        ) as mock_factory:
            mock_provider = MagicMock()
            mock_provider.create_ticket = AsyncMock(return_value=mock_result)
            mock_provider.create_subtasks_for = AsyncMock(return_value=([], [], [], []))
            mock_provider.build_payload.return_value = {
                "work_item_type": "User Story",
                "fields": [{"op": "add", "path": "/fields/System.Title", "value": "Test"}],
            }
            mock_factory.return_value = mock_provider

            response = client.post("/api/v1/tickets", json={
                "story_id": "story-azure",
                "integration_type": "azure_devops",
                "project_key": "PROJ",
                "issue_type": "Story",
            })

        assert response.status_code == 201
        data = response.json()
        assert data["ticket_id"] == "42"
        assert data["provider"] == "azure_devops"


class TestIntegrationHealthEndpoint:
    def test_health_returns_jira_not_configured(self):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        db = Session()
        settings = make_settings(JIRA_BASE_URL="", JIRA_API_TOKEN="")
        app = apply_mock_auth(create_app())
        app.dependency_overrides[get_integration_service] = lambda: TicketIntegrationService(
            db=db, settings=settings
        )

        client = TestClient(app)
        response = client.get("/api/v1/integration/health")

        assert response.status_code == 200
        data = response.json()
        assert data["jira"] == "not_configured"
        assert data["azure_devops"] == "not_configured"
