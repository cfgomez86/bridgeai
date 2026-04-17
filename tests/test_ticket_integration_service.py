import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.database.session import Base
from app.domain.ticket_integration import TicketResult
from app.models.user_story import UserStory as UserStoryModel
from app.services.ticket_integration_service import (
    StoryNotFoundError,
    TicketIntegrationService,
    UnsupportedProviderError,
)


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


def make_db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def insert_story(db, story_id: str = "story-1") -> UserStoryModel:
    story = UserStoryModel(
        id=story_id,
        requirement_id="req-1",
        impact_analysis_id="ana-1",
        project_id="proj-1",
        title="Test Story",
        story_description="As a user...",
        acceptance_criteria=json.dumps(["AC1", "AC2"]),
        technical_tasks=json.dumps(["Task1"]),
        definition_of_done=json.dumps(["DoD1"]),
        risk_notes=json.dumps([]),
        story_points=5,
        risk_level="MEDIUM",
        generation_time_seconds=1.0,
        created_at=datetime.now(timezone.utc),
    )
    db.add(story)
    db.commit()
    return story


class TestCreateTicket:
    def test_raises_story_not_found(self):
        db = make_db_session()
        service = TicketIntegrationService(db, make_settings())

        with pytest.raises(StoryNotFoundError):
            service.create_ticket("nonexistent-id", "jira", "PROJ", "Story")

    def test_raises_unsupported_provider(self):
        db = make_db_session()
        insert_story(db)
        service = TicketIntegrationService(db, make_settings())

        with pytest.raises(UnsupportedProviderError):
            service.create_ticket("story-1", "servicenow", "PROJ", "Story")

    def test_creates_ticket_successfully(self):
        db = make_db_session()
        insert_story(db)
        settings = make_settings()
        service = TicketIntegrationService(db, settings)

        mock_result = TicketResult(
            external_id="PROJ-1",
            url="https://test.atlassian.net/browse/PROJ-1",
            provider="jira",
            status="CREATED",
        )

        with patch(
            "app.services.ticket_integration_service.TicketIntegrationService._get_provider"
        ) as mock_provider_factory:
            mock_provider = MagicMock()
            mock_provider.create_ticket.return_value = mock_result
            mock_provider.build_payload.return_value = {"fields": {"summary": "Test Story"}}
            mock_provider_factory.return_value = mock_provider

            result, is_duplicate = service.create_ticket(
                "story-1", "jira", "PROJ", "Story"
            )

        assert result.external_id == "PROJ-1"
        assert result.status == "CREATED"
        assert is_duplicate is False

    def test_returns_duplicate_on_second_call(self):
        db = make_db_session()
        insert_story(db)
        settings = make_settings()
        service = TicketIntegrationService(db, settings)

        mock_result = TicketResult(
            external_id="PROJ-1",
            url="https://test.atlassian.net/browse/PROJ-1",
            provider="jira",
            status="CREATED",
        )

        with patch(
            "app.services.ticket_integration_service.TicketIntegrationService._get_provider"
        ) as mock_provider_factory:
            mock_provider = MagicMock()
            mock_provider.create_ticket.return_value = mock_result
            mock_provider.build_payload.return_value = {"fields": {"summary": "Test Story"}}
            mock_provider_factory.return_value = mock_provider

            # First call
            service.create_ticket("story-1", "jira", "PROJ", "Story")
            # Second call — should be duplicate
            result, is_duplicate = service.create_ticket("story-1", "jira", "PROJ", "Story")

        assert is_duplicate is True
        assert result.status == "DUPLICATE"
        # Provider should only have been called once
        assert mock_provider.create_ticket.call_count == 1

    def test_persists_failed_status_on_error(self):
        from urllib.error import HTTPError

        db = make_db_session()
        insert_story(db)
        settings = make_settings()
        service = TicketIntegrationService(db, settings)

        with patch(
            "app.services.ticket_integration_service.TicketIntegrationService._get_provider"
        ) as mock_provider_factory:
            mock_provider = MagicMock()
            mock_provider.create_ticket.side_effect = HTTPError(
                url="", code=401, msg="Unauthorized", hdrs=None, fp=None
            )
            mock_provider.build_payload.return_value = {"fields": {"summary": "Test Story"}}
            mock_provider_factory.return_value = mock_provider

            with pytest.raises(HTTPError):
                service.create_ticket("story-1", "jira", "PROJ", "Story")

        from app.models.ticket_integration import TicketIntegration
        record = db.query(TicketIntegration).filter_by(story_id="story-1").first()
        assert record is not None
        assert record.status == "FAILED"


class TestHealthCheck:
    def test_health_check_not_configured(self):
        db = make_db_session()
        settings = make_settings(JIRA_BASE_URL="", JIRA_API_TOKEN="")
        service = TicketIntegrationService(db, settings)

        result = service.health_check()
        assert result["jira"] == "not_configured"
        assert result["azure_devops"] == "not_configured"

    def test_health_check_jira_healthy(self):
        import json as _json
        from unittest.mock import MagicMock

        db = make_db_session()
        settings = make_settings()
        service = TicketIntegrationService(db, settings)

        mock_response = MagicMock()
        mock_response.read.return_value = _json.dumps({"accountId": "abc"}).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("app.services.ticket_providers.jira.urlopen", return_value=mock_response):
            result = service.health_check()

        assert result["jira"] == "healthy"
