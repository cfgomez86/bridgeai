"""Integration tests for GET /api/v1/system/quality/live.

Verifies the response shape and that scores are correctly partitioned by
`user_stories.entity_not_found`.
"""
import json
import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base, get_db
from app.main import create_app
from app.models.story_quality_score import StoryQualityScore
from app.models.user_story import UserStory
from tests.integration.auth_helpers import (
    TEST_CONNECTION_ID,
    TEST_TENANT_ID,
    apply_mock_auth,
    seed_source_connection,
)


def _seed_story_with_score(db, *, story_id: str, entity_not_found: bool, overall: float) -> None:
    db.add(UserStory(
        id=story_id,
        tenant_id=TEST_TENANT_ID,
        source_connection_id=TEST_CONNECTION_ID,
        requirement_id=f"req-{story_id}",
        impact_analysis_id=f"ana-{story_id}",
        project_id="proj-x",
        title=f"Story {story_id}",
        story_description="desc",
        acceptance_criteria=json.dumps(["AC1"]),
        subtasks=json.dumps({"frontend": [], "backend": [{"title": "T", "description": "D"}], "configuration": []}),
        definition_of_done=json.dumps(["DoD"]),
        risk_notes=json.dumps([]),
        story_points=1,
        risk_level="LOW",
        generation_time_seconds=0.1,
        entity_not_found=entity_not_found,
        created_at=datetime.now(timezone.utc),
    ))
    db.add(StoryQualityScore(
        id=uuid.uuid4(),
        tenant_id=TEST_TENANT_ID,
        story_id=story_id,
        completeness=overall,
        specificity=overall,
        feasibility=overall,
        risk_coverage=overall,
        language_consistency=overall,
        overall=overall,
        judge_model="test-judge",
        dispersion=0.5,
        samples_used=1,
        evaluated_at=datetime.utcnow(),
    ))


def _make_client_with_seed(seed_fn) -> TestClient:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    db = Session()
    seed_source_connection(db)
    seed_fn(db)
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


def test_live_quality_returns_separated_buckets():
    def seed(db):
        _seed_story_with_score(db, story_id="org-1", entity_not_found=False, overall=8.0)
        _seed_story_with_score(db, story_id="org-2", entity_not_found=False, overall=9.0)
        _seed_story_with_score(db, story_id="frc-1", entity_not_found=True, overall=4.0)

    client = _make_client_with_seed(seed)

    response = client.get("/api/v1/system/quality/live?days=30")
    assert response.status_code == 200
    data = response.json()

    assert data["window_days"] == 30
    assert data["organic"]["count"] == 2
    assert data["organic"]["avg_overall"] == 8.5
    assert data["forced"]["count"] == 1
    assert data["forced"]["avg_overall"] == 4.0
    assert data["all"]["count"] == 3
    assert data["all"]["avg_overall"] == 7.0


def test_live_quality_with_no_data_returns_zero_counts():
    client = _make_client_with_seed(lambda _db: None)

    response = client.get("/api/v1/system/quality/live")
    assert response.status_code == 200
    data = response.json()

    assert data["window_days"] == 30  # default
    assert data["organic"]["count"] == 0
    assert data["organic"]["avg_overall"] is None
    assert data["forced"]["count"] == 0
    assert data["forced"]["avg_overall"] is None
    assert data["all"]["count"] == 0


def test_live_quality_clamps_days_param():
    """`days` must be clamped to [1, 365] to prevent silly windows."""
    client = _make_client_with_seed(lambda _db: None)

    too_small = client.get("/api/v1/system/quality/live?days=0")
    assert too_small.status_code == 200
    assert too_small.json()["window_days"] == 1

    too_big = client.get("/api/v1/system/quality/live?days=10000")
    assert too_big.status_code == 200
    assert too_big.json()["window_days"] == 365
