"""Integration tests for story quality endpoints."""
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.database.session import Base, get_db
from app.main import create_app
from app.models.user_story import UserStory
from app.services.story_quality_judge import StubQualityJudge, get_quality_judge
from tests.integration.auth_helpers import (
    TEST_CONNECTION_ID,
    TEST_TENANT_ID,
    apply_mock_auth,
    seed_source_connection,
)

_STORY_ID = "story-quality-001"


def _make_quality_client():
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
        requirement_id="req-q1",
        impact_analysis_id="ana-q1",
        project_id="proj-q1",
        title="Quality Test Story",
        story_description="As a user, I want quality metrics.",
        acceptance_criteria=json.dumps(["AC1", "AC2"]),
        subtasks=json.dumps({
            "frontend": [],
            "backend": [
                {"title": "Implement quality service", "description": "Add quality scoring service."},
            ],
            "configuration": [],
        }),
        definition_of_done=json.dumps(["Tests pass"]),
        risk_notes=json.dumps(["Risk A"]),
        story_points=3,
        risk_level="LOW",
        generation_time_seconds=1.0,
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

    # Use Settings with AI_PROVIDER=stub to ensure StubQualityJudge is used
    stub_settings = Settings(
        DATABASE_URL="sqlite:///:memory:",
        AI_PROVIDER="stub",
        AI_JUDGE_PROVIDER="",
        AI_JUDGE_ENABLED=True,
    )

    app = apply_mock_auth(create_app())
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: stub_settings
    return TestClient(app)


@pytest.fixture(scope="module")
def quality_client():
    return _make_quality_client()


def test_get_quality_without_score(quality_client):
    """GET quality returns structural metrics and null judge when not evaluated."""
    response = quality_client.get(f"/api/v1/stories/{_STORY_ID}/quality")
    assert response.status_code == 200
    data = response.json()
    assert data["story_id"] == _STORY_ID
    assert "structural" in data
    structural = data["structural"]
    assert "schema_valid" in structural
    assert "ac_count" in structural
    assert "subtask_count" in structural
    assert "citation_grounding_ratio" in structural
    assert data["judge"] is None


def test_post_evaluate_persists_score(quality_client):
    """POST evaluate returns judge scores and persists them."""
    response = quality_client.post(
        f"/api/v1/stories/{_STORY_ID}/quality/evaluate",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["judge"] is not None
    judge = data["judge"]
    assert judge["overall"] == 7.0
    assert judge["judge_model"] == "stub"
    assert judge["justification"] == "Stub evaluation"
    assert "evaluated_at" in judge


def test_get_quality_after_evaluate_has_judge(quality_client):
    """After evaluating, GET quality returns the judge scores."""
    response = quality_client.get(f"/api/v1/stories/{_STORY_ID}/quality")
    assert response.status_code == 200
    data = response.json()
    assert data["judge"] is not None
    assert data["judge"]["overall"] == 7.0


def test_get_quality_not_found_story(quality_client):
    response = quality_client.get("/api/v1/stories/nonexistent-story-yyy/quality")
    assert response.status_code == 404
