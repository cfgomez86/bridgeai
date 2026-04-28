"""Integration tests for story feedback endpoints."""
import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base, get_db
from app.main import create_app
from app.models.user_story import UserStory
from tests.integration.auth_helpers import (
    TEST_CONNECTION_ID,
    TEST_TENANT_ID,
    TEST_USER_ID,
    apply_mock_auth,
    seed_source_connection,
)

_STORY_ID = "story-feedback-001"


@pytest.fixture(scope="module")
def feedback_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    db = Session()
    seed_source_connection(db)
    db.add(UserStory(
        id=_STORY_ID,
        tenant_id=TEST_TENANT_ID,
        source_connection_id=TEST_CONNECTION_ID,
        requirement_id="req-fb1",
        impact_analysis_id="ana-fb1",
        project_id="proj-fb1",
        title="Feedback Test Story",
        story_description="Description for feedback.",
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


def test_post_feedback_returns_200(feedback_client):
    response = feedback_client.post(
        f"/api/v1/stories/{_STORY_ID}/feedback",
        json={"rating": "thumbs_up", "comment": "Great story!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["rating"] == "thumbs_up"
    assert data["comment"] == "Great story!"
    assert data["user_id"] == TEST_USER_ID
    assert data["story_id"] == _STORY_ID


def test_post_feedback_upsert_same_user(feedback_client):
    """Second POST from same user should update (upsert), not duplicate."""
    response = feedback_client.post(
        f"/api/v1/stories/{_STORY_ID}/feedback",
        json={"rating": "thumbs_down", "comment": "Changed my mind."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["rating"] == "thumbs_down"
    assert data["comment"] == "Changed my mind."


def test_get_feedback_returns_upserted_value(feedback_client):
    response = feedback_client.get(f"/api/v1/stories/{_STORY_ID}/feedback")
    assert response.status_code == 200
    data = response.json()
    # Should reflect the last upsert (thumbs_down)
    assert data["rating"] == "thumbs_down"
    assert data["user_id"] == TEST_USER_ID


def test_post_feedback_invalid_rating_returns_400(feedback_client):
    response = feedback_client.post(
        f"/api/v1/stories/{_STORY_ID}/feedback",
        json={"rating": "invalid_value"},
    )
    assert response.status_code == 400


def test_get_feedback_not_found_story_returns_correct_handling(feedback_client):
    """GET feedback on nonexistent story returns None (null body) or 404."""
    response = feedback_client.get("/api/v1/stories/nonexistent-story-xxx/feedback")
    # The get_feedback endpoint doesn't validate story existence, returns null
    # (the tenant check on feedback just returns None when no record found)
    assert response.status_code == 200
    assert response.json() is None
