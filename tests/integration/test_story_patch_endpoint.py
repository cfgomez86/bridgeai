"""Integration tests for PATCH /api/v1/stories/{story_id}."""
import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base, get_db
from app.main import create_app
from app.models.ticket_integration import TicketIntegration
from app.models.user_story import UserStory
from tests.integration.auth_helpers import (
    TEST_CONNECTION_ID,
    TEST_TENANT_ID,
    apply_mock_auth,
    seed_source_connection,
)

_STORY_ID = "story-patch-001"
_LOCKED_STORY_ID = "story-patch-locked-001"


def _make_engine_and_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine)


def _seed_story(db, story_id: str):
    db.add(UserStory(
        id=story_id,
        tenant_id=TEST_TENANT_ID,
        source_connection_id=TEST_CONNECTION_ID,
        requirement_id="req-p1",
        impact_analysis_id="ana-p1",
        project_id="proj-p1",
        title="Original Title",
        story_description="Original description.",
        acceptance_criteria=json.dumps(["AC1"]),
        subtasks=json.dumps({
            "frontend": [],
            "backend": [{"title": "Do something", "description": "Some details."}],
            "configuration": [],
        }),
        definition_of_done=json.dumps(["DoD1"]),
        risk_notes=json.dumps(["Risk 1"]),
        story_points=3,
        risk_level="LOW",
        generation_time_seconds=1.0,
        created_at=datetime.now(timezone.utc),
    ))


def _seed_locked_story(db):
    db.add(UserStory(
        id=_LOCKED_STORY_ID,
        tenant_id=TEST_TENANT_ID,
        source_connection_id=TEST_CONNECTION_ID,
        requirement_id="req-locked",
        impact_analysis_id="ana-locked",
        project_id="proj-locked",
        title="Locked Story",
        story_description="This story has a ticket.",
        acceptance_criteria=json.dumps(["AC1"]),
        subtasks=json.dumps({
            "frontend": [], "backend": [
                {"title": "Backend task title here", "description": "Some description text here."},
            ], "configuration": [],
        }),
        definition_of_done=json.dumps(["DoD1"]),
        risk_notes=json.dumps([]),
        story_points=2,
        risk_level="LOW",
        generation_time_seconds=0.5,
        created_at=datetime.now(timezone.utc),
    ))
    # Add a CREATED ticket integration to lock it
    db.add(TicketIntegration(
        id="ticket-locked-001",
        tenant_id=TEST_TENANT_ID,
        story_id=_LOCKED_STORY_ID,
        provider="jira",
        project_key="TEST",
        issue_type="Story",
        external_ticket_id="TEST-1",
        status="CREATED",
        retry_count=0,
        error_message=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    ))


@pytest.fixture(scope="module")
def patch_client():
    engine, Session = _make_engine_and_session()
    db = Session()
    seed_source_connection(db)
    _seed_story(db, _STORY_ID)
    _seed_locked_story(db)
    db.commit()
    db.close()

    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app = apply_mock_auth(create_app())
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_patch_story_happy_path(patch_client):
    response = patch_client.patch(
        f"/api/v1/stories/{_STORY_ID}",
        json={
            "source_connection_id": TEST_CONNECTION_ID,
            "title": "Updated Title",
            "story_points": 5,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["story_points"] == 5
    assert data["is_locked"] is False


def test_patch_story_empty_subtasks(patch_client):
    response = patch_client.patch(
        f"/api/v1/stories/{_STORY_ID}",
        json={
            "source_connection_id": TEST_CONNECTION_ID,
            "subtasks": {
                "frontend": [],
                "backend": [],
                "configuration": [],
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["subtasks"]["backend"] == []


def test_patch_story_locked_returns_409(patch_client):
    response = patch_client.patch(
        f"/api/v1/stories/{_LOCKED_STORY_ID}",
        json={
            "source_connection_id": TEST_CONNECTION_ID,
            "title": "Should not update",
        },
    )
    assert response.status_code == 409
    assert "locked" in response.json()["detail"].lower()


def test_patch_story_not_found_returns_404(patch_client):
    response = patch_client.patch(
        "/api/v1/stories/nonexistent-story",
        json={
            "source_connection_id": TEST_CONNECTION_ID,
            "title": "New title",
        },
    )
    assert response.status_code == 404


def test_get_story_has_is_locked_field(patch_client):
    response = patch_client.get(f"/api/v1/stories/{_STORY_ID}")
    assert response.status_code == 200
    data = response.json()
    assert "is_locked" in data
