"""Tests for Phase 5b hardening: jitter backoff, query endpoints, audit log."""
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
from app.database.session import Base
from app.domain.ticket_integration import TicketResult
from app.main import create_app
from app.models.ticket_integration import IntegrationAuditLog, TicketIntegration
from app.models.user_story import UserStory as UserStoryModel
from app.api.routes.ticket_integration import get_integration_service
from app.services.ticket_integration_service import TicketIntegrationService
from app.services.ticket_providers.jira import JiraTicketProvider
from app.domain.user_story import UserStory


def make_settings(**kwargs) -> Settings:
    defaults = dict(
        DATABASE_URL="sqlite:///:memory:",
        JIRA_BASE_URL="https://test.atlassian.net",
        JIRA_USER_EMAIL="user@test.com",
        JIRA_API_TOKEN="token123",
        JIRA_MAX_RETRIES=2,
        JIRA_RETRY_DELAY_SECONDS=1,
    )
    defaults.update(kwargs)
    return Settings(**defaults)


def make_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def insert_story(db, story_id: str = "story-harden-1") -> UserStoryModel:
    story = UserStoryModel(
        id=story_id,
        requirement_id="req-1",
        impact_analysis_id="ana-1",
        project_id="proj-1",
        title="Hardening Story",
        story_description="As a user...",
        acceptance_criteria=json.dumps(["AC1"]),
        subtasks=json.dumps({"frontend": [], "backend": ["Task1"], "configuration": []}),
        definition_of_done=json.dumps(["DoD1"]),
        risk_notes=json.dumps([]),
        story_points=3,
        risk_level="LOW",
        generation_time_seconds=0.5,
        created_at=datetime.now(timezone.utc),
    )
    db.add(story)
    db.commit()
    return story


def make_domain_story() -> UserStory:
    return UserStory(
        story_id=str(uuid.uuid4()),
        requirement_id="req-1",
        impact_analysis_id="ana-1",
        project_id="proj-1",
        title="Story",
        story_description="Description",
        acceptance_criteria=["AC1"],
        subtasks={"frontend": [], "backend": ["Task1"], "configuration": []},
        definition_of_done=["DoD1"],
        risk_notes=[],
        story_points=3,
        risk_level="LOW",
        created_at=datetime.now(timezone.utc),
        generation_time_seconds=0.5,
    )


class TestJitterBackoff:
    def test_backoff_returns_value_within_range(self):
        settings = make_settings(JIRA_RETRY_DELAY_SECONDS=4)
        provider = JiraTicketProvider(settings)

        for attempt in range(3):
            wait = provider._backoff_seconds(attempt, 4)
            cap = 4 * (2 ** attempt)
            assert 0 <= wait <= cap

    def test_backoff_uses_retry_after_on_429(self):
        settings = make_settings()
        provider = JiraTicketProvider(settings)

        wait = provider._backoff_seconds(0, 5, retry_after="30")
        assert wait == 30.0

    def test_backoff_falls_back_to_jitter_on_missing_retry_after(self):
        settings = make_settings(JIRA_RETRY_DELAY_SECONDS=2)
        provider = JiraTicketProvider(settings)

        wait = provider._backoff_seconds(0, 2, retry_after=None)
        assert 0 <= wait <= 2

    async def test_429_triggers_retry(self):
        from urllib.error import HTTPError

        settings = make_settings(JIRA_MAX_RETRIES=2, JIRA_RETRY_DELAY_SECONDS=0)
        provider = JiraTicketProvider(settings)
        story = make_domain_story()

        error_429 = HTTPError(url="", code=429, msg="Too Many Requests", hdrs=None, fp=None)

        with patch.object(provider, "_request", new=AsyncMock(side_effect=[error_429, {"key": "PROJ-99"}])):
            result = await provider.create_ticket(story, "PROJ", "Story")

        assert result.status == "CREATED"


class TestAuditPayloadCapture:
    async def test_audit_log_stores_full_jira_payload(self):
        db = make_db()
        insert_story(db, "story-audit-payload")
        settings = make_settings()
        service = TicketIntegrationService(db, settings)

        mock_result = TicketResult(
            external_id="PROJ-7",
            url="https://test.atlassian.net/browse/PROJ-7",
            provider="jira",
            status="CREATED",
        )

        with patch(
            "app.services.ticket_integration_service.TicketIntegrationService._get_provider"
        ) as mock_factory:
            mock_provider = MagicMock()
            mock_provider.create_ticket = AsyncMock(return_value=mock_result)
            mock_provider.create_subtasks_for = AsyncMock(return_value=([], [], [], []))
            mock_provider.build_payload.return_value = {
                "fields": {"summary": "Hardening Story", "project": {"key": "PROJ"}}
            }
            mock_factory.return_value = mock_provider

            await service.create_ticket("story-audit-payload", "jira", "PROJ", "Story")

        logs = db.query(IntegrationAuditLog).filter_by(story_id="story-audit-payload").all()
        assert len(logs) == 1
        payload_data = json.loads(logs[0].payload)
        assert "fields" in payload_data
        assert payload_data["fields"]["summary"] == "Hardening Story"


class TestQueryEndpoints:
    def _make_client(self, story_id: str = "story-query-1"):
        db = make_db()
        insert_story(db, story_id)
        settings = make_settings()
        app = create_app()
        app.dependency_overrides[get_integration_service] = lambda: TicketIntegrationService(
            db=db, settings=settings
        )
        return TestClient(app), db, settings

    def test_get_tickets_returns_empty_list(self):
        client, db, _ = self._make_client("story-empty")
        response = client.get("/api/v1/tickets/story-empty")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_tickets_returns_created_integration(self):
        client, db, settings = self._make_client("story-has-ticket")

        now = datetime.now(timezone.utc)
        record = TicketIntegration(
            id=str(uuid.uuid4()),
            story_id="story-has-ticket",
            provider="jira",
            project_key="PROJ",
            issue_type="Story",
            external_ticket_id="PROJ-55",
            status="CREATED",
            retry_count=0,
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        db.add(record)
        db.commit()

        response = client.get("/api/v1/tickets/story-has-ticket")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["external_ticket_id"] == "PROJ-55"
        assert data[0]["status"] == "CREATED"
        assert data[0]["provider"] == "jira"

    def test_get_audit_returns_empty_list(self):
        client, _, _ = self._make_client("story-no-audit")
        response = client.get("/api/v1/tickets/story-no-audit/audit")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_audit_returns_log_entries(self):
        client, db, _ = self._make_client("story-with-audit")

        now = datetime.now(timezone.utc)
        log = IntegrationAuditLog(
            id=str(uuid.uuid4()),
            story_id="story-with-audit",
            provider="jira",
            action="create_ticket",
            payload=json.dumps({"fields": {"summary": "Test"}}),
            response=json.dumps({"external_id": "PROJ-3"}),
            status="CREATED",
            timestamp=now,
        )
        db.add(log)
        db.commit()

        response = client.get("/api/v1/tickets/story-with-audit/audit")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["action"] == "create_ticket"
        assert data[0]["status"] == "CREATED"
        payload = json.loads(data[0]["payload"])
        assert payload["fields"]["summary"] == "Test"

    def test_audit_entries_ordered_newest_first(self):
        client, db, _ = self._make_client("story-ordered")

        from datetime import timedelta
        base = datetime.now(timezone.utc)
        for i, action in enumerate(["attempt_1", "attempt_2", "attempt_3"]):
            db.add(IntegrationAuditLog(
                id=str(uuid.uuid4()),
                story_id="story-ordered",
                provider="jira",
                action=action,
                payload=None,
                response=None,
                status="FAILED" if i < 2 else "CREATED",
                timestamp=base + timedelta(seconds=i),
            ))
        db.commit()

        response = client.get("/api/v1/tickets/story-ordered/audit")
        data = response.json()
        assert len(data) == 3
        assert data[0]["action"] == "attempt_3"
        assert data[2]["action"] == "attempt_1"
