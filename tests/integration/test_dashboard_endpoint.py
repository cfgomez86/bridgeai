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


def _seed_story(
    db,
    story_id: str,
    title: str = "Story",
    points: int = 3,
    risk: str = "LOW",
    entity_not_found: bool = False,
    was_forced: bool = False,
):
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
        entity_not_found=entity_not_found,
        was_forced=was_forced,
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
    assert data["quality_avg_organic"] is None
    assert data["quality_count_organic"] == 0
    assert data["quality_avg_forced"] is None
    assert data["quality_count_forced"] == 0
    assert data["quality_count_creation_bypass"] == 0
    assert data["quality_count_override"] == 0
    assert data["tickets_failed_count"] == 0
    assert data["avg_generation_time_seconds"] is None
    assert data["unnecessary_force_count"] == 0
    assert data["quality_organic_avg_completeness"] is None
    assert data["quality_organic_avg_specificity"] is None
    assert data["quality_organic_avg_feasibility"] is None
    assert data["quality_organic_avg_risk_coverage"] is None
    assert data["quality_organic_avg_language_consistency"] is None
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
    # Fixture's only score belongs to a story without entity_not_found, so
    # it lands in the organic bucket; forced bucket is empty.
    assert data["quality_avg_organic"] == pytest.approx(7.6)
    assert data["quality_count_organic"] == 1
    assert data["quality_avg_forced"] is None
    assert data["quality_count_forced"] == 0
    assert data["quality_count_creation_bypass"] == 0
    assert data["quality_count_override"] == 0
    # Fixture seeds story-1 with completeness=8, specificity=7, feasibility=8,
    # risk_coverage=6, language_consistency=9 — all on the organic bucket.
    assert data["quality_organic_avg_completeness"] == pytest.approx(8.0)
    assert data["quality_organic_avg_specificity"] == pytest.approx(7.0)
    assert data["quality_organic_avg_feasibility"] == pytest.approx(8.0)
    assert data["quality_organic_avg_risk_coverage"] == pytest.approx(6.0)
    assert data["quality_organic_avg_language_consistency"] == pytest.approx(9.0)
    # No tickets failed, no unnecessary force in this fixture.
    assert data["tickets_failed_count"] == 0
    assert data["unnecessary_force_count"] == 0
    # generation_time_seconds default is 0.5 in _seed_story; both stories
    # contribute (story-1 + story-2).
    assert data["avg_generation_time_seconds"] == pytest.approx(0.5)
    assert data["tickets_by_provider"] == {"jira": 1}
    assert data["stories_by_risk"] == {"LOW": 1, "MEDIUM": 0, "HIGH": 1}


def test_stats_with_window_filters_old_data(populated_client):
    r = populated_client.get("/api/v1/dashboard/stats?window_days=30")
    assert r.status_code == 200
    data = r.json()
    assert data["window_days"] == 30
    # Test data was created "now", so still within 30d window
    assert data["stories_count"] == 2


def test_stats_partitions_quality_with_was_forced():
    """Three scored stories — organic + creation_bypass + override — must
    populate the new sub-counts and per-bucket averages distinctly."""
    Session = _make_session()
    db = Session()
    seed_source_connection(db)

    now = datetime.now(timezone.utc)

    _seed_story(db, "org-1", title="Organic")
    _seed_story(db, "creation-1", title="Creation bypass", entity_not_found=True, was_forced=False)
    _seed_story(db, "override-1", title="User override", entity_not_found=True, was_forced=True)

    db.add(StoryQualityScore(
        id=uuid.uuid4(), tenant_id=TEST_TENANT_ID, story_id="org-1",
        completeness=8, specificity=8, feasibility=8, risk_coverage=8,
        language_consistency=8, overall=8.0, evaluated_at=now,
    ))
    db.add(StoryQualityScore(
        id=uuid.uuid4(), tenant_id=TEST_TENANT_ID, story_id="creation-1",
        completeness=5, specificity=5, feasibility=5, risk_coverage=5,
        language_consistency=5, overall=5.0, evaluated_at=now,
    ))
    db.add(StoryQualityScore(
        id=uuid.uuid4(), tenant_id=TEST_TENANT_ID, story_id="override-1",
        completeness=4, specificity=4, feasibility=4, risk_coverage=4,
        language_consistency=4, overall=4.0, evaluated_at=now,
    ))
    db.commit()
    db.close()

    client = _make_client(Session)
    r = client.get("/api/v1/dashboard/stats")
    assert r.status_code == 200
    data = r.json()

    assert data["quality_avg_organic"] == pytest.approx(8.0)
    assert data["quality_count_organic"] == 1

    assert data["quality_avg_forced"] == pytest.approx(4.5)
    assert data["quality_count_forced"] == 2
    assert data["quality_count_creation_bypass"] == 1
    assert data["quality_count_override"] == 1

    assert data["quality_avg_overall"] == pytest.approx(17.0 / 3.0)
    assert data["quality_evaluated_count"] == 3


def test_stats_counts_failed_tickets():
    """Tickets with status=FAILED feed `tickets_failed_count` while CREATED
    keeps feeding `tickets_count` — the dashboard sees both numbers."""
    Session = _make_session()
    db = Session()
    seed_source_connection(db)
    _seed_story(db, "story-1")
    now = datetime.now(timezone.utc)

    # 2 successful + 1 failed.
    for ext_id in ("PROJ-1", "PROJ-2"):
        db.add(TicketIntegration(
            id=str(uuid.uuid4()), tenant_id=TEST_TENANT_ID, story_id="story-1",
            provider="jira", project_key="PROJ", issue_type="Story",
            external_ticket_id=ext_id, status="CREATED", retry_count=0,
            created_at=now, updated_at=now,
        ))
    db.add(TicketIntegration(
        id=str(uuid.uuid4()), tenant_id=TEST_TENANT_ID, story_id="story-1",
        provider="jira", project_key="PROJ", issue_type="Story",
        external_ticket_id=None, status="FAILED", retry_count=2,
        error_message="invalid token", created_at=now, updated_at=now,
    ))
    db.commit()
    db.close()

    client = _make_client(Session)
    r = client.get("/api/v1/dashboard/stats")
    assert r.status_code == 200
    data = r.json()

    assert data["tickets_count"] == 2
    assert data["tickets_failed_count"] == 1


def test_stats_counts_unnecessary_force():
    """A story persisted with was_forced=True but entity_not_found=False is a
    UX smell — count surfaces it even if the rest of the dashboard is empty."""
    Session = _make_session()
    db = Session()
    seed_source_connection(db)

    _seed_story(db, "story-org", entity_not_found=False, was_forced=False)
    _seed_story(db, "story-unnecessary", entity_not_found=False, was_forced=True)
    _seed_story(db, "story-override", entity_not_found=True, was_forced=True)
    db.commit()
    db.close()

    client = _make_client(Session)
    r = client.get("/api/v1/dashboard/stats")
    assert r.status_code == 200
    data = r.json()

    # Only the (False, True) combination counts as unnecessary.
    assert data["unnecessary_force_count"] == 1


def test_stats_avg_generation_time():
    """avg_generation_time_seconds averages user_stories.generation_time_seconds."""
    Session = _make_session()
    db = Session()
    seed_source_connection(db)
    now = datetime.now(timezone.utc)

    for sid, gen_time in (("s-1", 2.0), ("s-2", 4.0)):
        db.add(UserStory(
            id=sid, tenant_id=TEST_TENANT_ID, source_connection_id=TEST_CONNECTION_ID,
            requirement_id="req-x", impact_analysis_id="ana-x", project_id="proj-x",
            title=sid, story_description="d",
            acceptance_criteria=json.dumps(["AC"]),
            subtasks=json.dumps({"frontend": [], "backend": [], "configuration": []}),
            definition_of_done=json.dumps([]), risk_notes=json.dumps([]),
            story_points=1, risk_level="LOW",
            generation_time_seconds=gen_time, created_at=now,
        ))
    db.commit()
    db.close()

    client = _make_client(Session)
    r = client.get("/api/v1/dashboard/stats")
    assert r.status_code == 200
    data = r.json()

    assert data["avg_generation_time_seconds"] == pytest.approx(3.0)


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
    response = r.json()
    assert len(response["items"]) == 1
    assert response["total"] == 1
    items = response["items"]
    assert items[0]["rating"] == "thumbs_down"
    assert items[0]["story_title"] == "Story Two"
    assert items[0]["comment"] == "Faltan detalles en los AC"
    assert items[0]["story_id"] == "story-2"


def test_feedback_comments_pagination(populated_client):
    r = populated_client.get("/api/v1/feedback/comments?limit=10&offset=10")
    assert r.status_code == 200
    response = r.json()
    assert response["items"] == []
    assert response["total"] == 2


def test_feedback_comments_rejects_invalid_rating(populated_client):
    r = populated_client.get("/api/v1/feedback/comments?rating=invalid_value")
    assert r.status_code == 400


def test_feedback_comments_empty_tenant_returns_empty_list(empty_client):
    r = empty_client.get("/api/v1/feedback/comments?rating=thumbs_down")
    assert r.status_code == 200
    response = r.json()
    assert response["items"] == []
    assert response["total"] == 0


def test_feedback_comments_non_admin_returns_403(populated_client):
    """Owner/member roles must NOT access feedback review — admin-only."""
    from datetime import datetime
    from app.api.dependencies import get_current_user
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
