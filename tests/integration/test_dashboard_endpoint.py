"""Integration tests for /dashboard/* endpoints."""
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base, get_db
from app.main import create_app
from app.models.impact_analysis import ImpactAnalysis
from app.models.requirement import Requirement
from app.models.story_feedback import StoryFeedback
from app.models.story_quality_score import StoryQualityScore
from app.models.ticket_integration import TicketIntegration
from app.models.user_story import UserStory
from tests.integration.auth_helpers import (
    TEST_CONNECTION_ID,
    TEST_TENANT_ID,
    TEST_USER_ID,
    apply_mock_auth,
    seed_source_connection,
)


def _make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)


def _make_client(Session):
    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app = apply_mock_auth(create_app())
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _seed_story(db, story_id: str, title: str = "Story", points: int = 3, risk: str = "LOW"):
    db.add(UserStory(
        id=story_id,
        tenant_id=TEST_TENANT_ID,
        source_connection_id=TEST_CONNECTION_ID,
        requirement_id="req-x",
        impact_analysis_id="ana-x",
        project_id="proj-x",
        title=title,
        story_description="desc",
        acceptance_criteria=json.dumps(["AC"]),
        subtasks=json.dumps({"frontend": [], "backend": [], "configuration": []}),
        definition_of_done=json.dumps([]),
        risk_notes=json.dumps([]),
        story_points=points,
        risk_level=risk,
        generation_time_seconds=0.5,
        created_at=datetime.now(timezone.utc),
    ))


@pytest.fixture(scope="function")
def empty_client():
    Session = _make_session()
    db = Session()
    seed_source_connection(db)
    db.commit()
    db.close()
    return _make_client(Session)


@pytest.fixture(scope="function")
def populated_client():
    Session = _make_session()
    db = Session()
    seed_source_connection(db)

    now = datetime.now(timezone.utc)

    # 2 requirements, 2 stories, 1 impact analysis, 1 ticket
    db.add(Requirement(
        id="req-1", tenant_id=TEST_TENANT_ID, source_connection_id=TEST_CONNECTION_ID,
        requirement_text="Foo", requirement_text_hash="h1", project_id="proj-x",
        intent="add", action="implement", entity="X", feature_type="auth", priority="P2",
        business_domain="d", technical_scope="back", estimated_complexity="M",
        keywords=json.dumps(["a"]), processing_time_seconds=0.1, created_at=now,
    ))
    db.add(Requirement(
        id="req-2", tenant_id=TEST_TENANT_ID, source_connection_id=TEST_CONNECTION_ID,
        requirement_text="Bar", requirement_text_hash="h2", project_id="proj-x",
        intent="add", action="implement", entity="X", feature_type="auth", priority="P2",
        business_domain="d", technical_scope="back", estimated_complexity="M",
        keywords=json.dumps(["a"]), processing_time_seconds=0.1, created_at=now,
    ))

    _seed_story(db, "story-1", title="Story One")
    _seed_story(db, "story-2", title="Story Two", risk="HIGH")

    db.add(ImpactAnalysis(
        id="ana-1", tenant_id=TEST_TENANT_ID, source_connection_id=TEST_CONNECTION_ID,
        requirement="Foo", risk_level="LOW", files_impacted=4, modules_impacted=2,
        analysis_summary="ok", created_at=now,
    ))

    db.add(TicketIntegration(
        id=str(uuid.uuid4()), tenant_id=TEST_TENANT_ID, story_id="story-1",
        provider="jira", project_key="PROJ", issue_type="Story",
        external_ticket_id="PROJ-100", status="CREATED", retry_count=0,
        created_at=now, updated_at=now,
    ))

    # 2 feedbacks: 1 thumbs_up, 1 thumbs_down with comment
    db.add(StoryFeedback(
        id=uuid.uuid4(), tenant_id=TEST_TENANT_ID, story_id="story-1",
        user_id=TEST_USER_ID, rating="thumbs_up", comment=None,
        created_at=now, updated_at=now,
    ))
    db.add(StoryFeedback(
        id=uuid.uuid4(), tenant_id=TEST_TENANT_ID, story_id="story-2",
        user_id=TEST_USER_ID, rating="thumbs_down",
        comment="Faltan detalles en los AC",
        created_at=now, updated_at=now,
    ))

    db.add(StoryQualityScore(
        id=uuid.uuid4(), tenant_id=TEST_TENANT_ID, story_id="story-1",
        completeness=8, specificity=7, feasibility=8, risk_coverage=6,
        language_consistency=9, overall=7.6, evaluated_at=now,
    ))

    db.commit()
    db.close()
    return _make_client(Session)


# ------------------------------- /dashboard/stats ---------------------------------


def test_stats_empty_tenant_returns_zeroes(empty_client):
    r = empty_client.get("/api/v1/dashboard/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["window_days"] is None
    assert data["requirements_count"] == 0
    assert data["stories_count"] == 0
    assert data["tickets_count"] == 0
    assert data["conversion_rate"] is None
    assert data["feedback_total"] == 0
    assert data["feedback_approval_rate"] is None
    assert data["quality_avg_overall"] is None
    assert data["quality_evaluated_count"] == 0
    assert data["tickets_by_provider"] == {}
    assert data["stories_by_risk"] == {"LOW": 0, "MEDIUM": 0, "HIGH": 0}


def test_stats_populated_tenant_returns_aggregations(populated_client):
    r = populated_client.get("/api/v1/dashboard/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["window_days"] is None
    assert data["requirements_count"] == 2
    assert data["stories_count"] == 2
    assert data["impact_analyses_count"] == 1
    assert data["tickets_count"] == 1
    assert data["conversion_rate"] == 0.5
    assert data["feedback_total"] == 2
    assert data["feedback_thumbs_up"] == 1
    assert data["feedback_thumbs_down"] == 1
    assert data["feedback_approval_rate"] == 0.5
    assert data["quality_avg_overall"] == pytest.approx(7.6)
    assert data["quality_evaluated_count"] == 1
    assert data["tickets_by_provider"] == {"jira": 1}
    assert data["stories_by_risk"] == {"LOW": 1, "MEDIUM": 0, "HIGH": 1}


def test_stats_with_window_filters_old_data(populated_client):
    r = populated_client.get("/api/v1/dashboard/stats?window_days=30")
    assert r.status_code == 200
    data = r.json()
    assert data["window_days"] == 30
    # Test data was created "now", so still within 30d window
    assert data["stories_count"] == 2


# ----------------------------- /dashboard/activity --------------------------------


def test_activity_returns_unified_feed(populated_client):
    r = populated_client.get("/api/v1/dashboard/activity?limit=10")
    assert r.status_code == 200
    events = r.json()
    assert isinstance(events, list)
    assert len(events) > 0
    titles = [e["title"] for e in events]
    assert any("Story" in t for t in titles)
    assert any("PROJ-100" in t for t in titles)
    assert any("riesgo" in t for t in titles)
    assert any("Feedback negativo" in t for t in titles)


def test_activity_respects_limit(populated_client):
    r = populated_client.get("/api/v1/dashboard/activity?limit=2")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_activity_empty_tenant_returns_empty_list(empty_client):
    r = empty_client.get("/api/v1/dashboard/activity")
    assert r.status_code == 200
    assert r.json() == []


# ----------------------------- /feedback/comments --------------------------------


def test_feedback_comments_returns_negative_only(populated_client):
    r = populated_client.get("/api/v1/feedback/comments?rating=thumbs_down&limit=10")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["rating"] == "thumbs_down"
    assert items[0]["story_title"] == "Story Two"
    assert items[0]["comment"] == "Faltan detalles en los AC"
    assert items[0]["story_id"] == "story-2"


def test_feedback_comments_pagination(populated_client):
    r = populated_client.get("/api/v1/feedback/comments?limit=10&offset=10")
    assert r.status_code == 200
    assert r.json() == []


def test_feedback_comments_rejects_invalid_rating(populated_client):
    r = populated_client.get("/api/v1/feedback/comments?rating=thumbs_up")
    assert r.status_code == 400


def test_feedback_comments_empty_tenant_returns_empty_list(empty_client):
    r = empty_client.get("/api/v1/feedback/comments?rating=thumbs_down")
    assert r.status_code == 200
    assert r.json() == []


def test_feedback_comments_non_admin_returns_403(populated_client):
    """Owner/member roles must NOT access feedback review — admin-only."""
    from datetime import datetime
    from app.core.auth0_auth import get_current_user
    from app.core.context import current_tenant_id, current_user_id
    from app.models.user import User

    async def mock_owner_auth() -> User:
        current_tenant_id.set(TEST_TENANT_ID)
        current_user_id.set(TEST_USER_ID)
        return User(
            id=TEST_USER_ID,
            auth0_user_id="auth0|owner",
            tenant_id=TEST_TENANT_ID,
            email="owner@bridgeai.test",
            name="Owner User",
            role="owner",
            created_at=datetime.utcnow(),
        )

    populated_client.app.dependency_overrides[get_current_user] = mock_owner_auth
    try:
        r = populated_client.get("/api/v1/feedback/comments?rating=thumbs_down")
        assert r.status_code == 403
    finally:
        populated_client.app.dependency_overrides[get_current_user] = mock_auth_admin


# Restore default mock for other tests that might run after
from tests.integration.auth_helpers import mock_auth as mock_auth_admin  # noqa: E402
