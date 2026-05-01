"""Unit tests for StoryQualityRepository bucket aggregation.

These cover the new `forced=` filter on the existing `avg_overall_since` /
`count_evaluated_since` methods, plus the `summary_since` triple-bucket query.
"""
import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base
from app.models.story_quality_score import StoryQualityScore
from app.models.user_story import UserStory
from app.repositories.story_quality_repository import StoryQualityRepository
from tests.unit.conftest import TEST_TENANT_ID, TEST_CONNECTION_ID

TENANT_B = "test-tenant-00000000-0000-0000-0000-000000000099"


def _make_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


def _seed_story(db, *, story_id: str, tenant_id: str, entity_not_found: bool) -> UserStory:
    story = UserStory(
        id=story_id,
        tenant_id=tenant_id,
        source_connection_id=TEST_CONNECTION_ID,
        requirement_id=f"req-{story_id}",
        impact_analysis_id=f"ana-{story_id}",
        project_id="proj-x",
        title=f"Story {story_id}",
        story_description="desc",
        acceptance_criteria=json.dumps(["AC1"]),
        subtasks=json.dumps({"frontend": [], "backend": [{"title": "T", "description": "D"}], "configuration": []}),
        definition_of_done=json.dumps(["DoD1"]),
        risk_notes=json.dumps([]),
        story_points=1,
        risk_level="LOW",
        generation_time_seconds=0.1,
        entity_not_found=entity_not_found,
        created_at=datetime.now(timezone.utc),
    )
    db.add(story)
    return story


def _seed_score(
    db,
    *,
    story_id: str,
    tenant_id: str,
    overall: float,
    dispersion: float | None = None,
    evaluated_at: datetime | None = None,
) -> StoryQualityScore:
    score = StoryQualityScore(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        story_id=story_id,
        completeness=overall,
        specificity=overall,
        feasibility=overall,
        risk_coverage=overall,
        language_consistency=overall,
        overall=overall,
        justification=None,
        judge_model="test-judge",
        dispersion=dispersion,
        samples_used=1,
        evidence=None,
        evaluated_at=evaluated_at or datetime.utcnow(),
    )
    db.add(score)
    return score


def test_summary_since_partitions_by_entity_not_found():
    engine = _make_engine()
    db = sessionmaker(bind=engine)()

    # Two organic stories: overall 8 and 9.
    _seed_story(db, story_id="org-1", tenant_id=TEST_TENANT_ID, entity_not_found=False)
    _seed_story(db, story_id="org-2", tenant_id=TEST_TENANT_ID, entity_not_found=False)
    _seed_score(db, story_id="org-1", tenant_id=TEST_TENANT_ID, overall=8.0, dispersion=0.5)
    _seed_score(db, story_id="org-2", tenant_id=TEST_TENANT_ID, overall=9.0, dispersion=0.7)

    # One forced story: overall 4.
    _seed_story(db, story_id="frc-1", tenant_id=TEST_TENANT_ID, entity_not_found=True)
    _seed_score(db, story_id="frc-1", tenant_id=TEST_TENANT_ID, overall=4.0, dispersion=1.2)
    db.commit()

    summary = StoryQualityRepository(db).summary_since(None)

    assert summary["organic"]["count"] == 2
    assert summary["organic"]["avg_overall"] == 8.5
    assert summary["forced"]["count"] == 1
    assert summary["forced"]["avg_overall"] == 4.0
    assert summary["all"]["count"] == 3
    # Weighted: (8 + 9 + 4) / 3 = 7.0
    assert summary["all"]["avg_overall"] == 7.0
    # Dispersion is averaged separately; just confirm it's present and numeric.
    assert summary["organic"]["avg_dispersion"] == 0.6
    assert summary["forced"]["avg_dispersion"] == 1.2


def test_summary_since_handles_empty_bucket():
    """When a bucket has no rows, avg=None and count=0; the other bucket still works."""
    engine = _make_engine()
    db = sessionmaker(bind=engine)()

    _seed_story(db, story_id="org-only", tenant_id=TEST_TENANT_ID, entity_not_found=False)
    _seed_score(db, story_id="org-only", tenant_id=TEST_TENANT_ID, overall=7.5)
    db.commit()

    summary = StoryQualityRepository(db).summary_since(None)

    assert summary["organic"]["count"] == 1
    assert summary["organic"]["avg_overall"] == 7.5
    assert summary["forced"]["count"] == 0
    assert summary["forced"]["avg_overall"] is None
    assert summary["forced"]["avg_dispersion"] is None
    assert summary["all"]["count"] == 1


def test_summary_since_isolates_other_tenants():
    """Stories and scores from another tenant must not leak into the summary."""
    engine = _make_engine()
    db = sessionmaker(bind=engine)()

    # Current tenant: 1 organic, overall 8.
    _seed_story(db, story_id="own-1", tenant_id=TEST_TENANT_ID, entity_not_found=False)
    _seed_score(db, story_id="own-1", tenant_id=TEST_TENANT_ID, overall=8.0)

    # Other tenant: a forced story with a wildly different score.
    _seed_story(db, story_id="other-1", tenant_id=TENANT_B, entity_not_found=True)
    _seed_score(db, story_id="other-1", tenant_id=TENANT_B, overall=2.0)
    db.commit()

    summary = StoryQualityRepository(db).summary_since(None)

    assert summary["organic"]["count"] == 1
    assert summary["organic"]["avg_overall"] == 8.0
    assert summary["forced"]["count"] == 0, "Other tenant's forced row must not appear"
    assert summary["all"]["count"] == 1


def test_summary_since_respects_time_window():
    engine = _make_engine()
    db = sessionmaker(bind=engine)()

    now = datetime.utcnow()
    _seed_story(db, story_id="recent", tenant_id=TEST_TENANT_ID, entity_not_found=False)
    _seed_story(db, story_id="old", tenant_id=TEST_TENANT_ID, entity_not_found=False)
    _seed_score(
        db, story_id="recent", tenant_id=TEST_TENANT_ID,
        overall=9.0, evaluated_at=now - timedelta(hours=1),
    )
    _seed_score(
        db, story_id="old", tenant_id=TEST_TENANT_ID,
        overall=3.0, evaluated_at=now - timedelta(days=60),
    )
    db.commit()

    summary = StoryQualityRepository(db).summary_since(now - timedelta(days=7))

    assert summary["organic"]["count"] == 1
    assert summary["organic"]["avg_overall"] == 9.0
    assert summary["all"]["count"] == 1


def test_avg_overall_since_with_forced_filter():
    """The new `forced=` kwarg on the existing method partitions correctly."""
    engine = _make_engine()
    db = sessionmaker(bind=engine)()

    _seed_story(db, story_id="org-1", tenant_id=TEST_TENANT_ID, entity_not_found=False)
    _seed_story(db, story_id="frc-1", tenant_id=TEST_TENANT_ID, entity_not_found=True)
    _seed_score(db, story_id="org-1", tenant_id=TEST_TENANT_ID, overall=8.0)
    _seed_score(db, story_id="frc-1", tenant_id=TEST_TENANT_ID, overall=4.0)
    db.commit()

    repo = StoryQualityRepository(db)

    # Default (no filter) — backwards-compatible behaviour.
    assert repo.avg_overall_since(None) == 6.0
    # Filtered.
    assert repo.avg_overall_since(None, forced=False) == 8.0
    assert repo.avg_overall_since(None, forced=True) == 4.0


def test_count_evaluated_since_with_forced_filter():
    engine = _make_engine()
    db = sessionmaker(bind=engine)()

    _seed_story(db, story_id="org-1", tenant_id=TEST_TENANT_ID, entity_not_found=False)
    _seed_story(db, story_id="org-2", tenant_id=TEST_TENANT_ID, entity_not_found=False)
    _seed_story(db, story_id="frc-1", tenant_id=TEST_TENANT_ID, entity_not_found=True)
    _seed_score(db, story_id="org-1", tenant_id=TEST_TENANT_ID, overall=8.0)
    _seed_score(db, story_id="org-2", tenant_id=TEST_TENANT_ID, overall=7.0)
    _seed_score(db, story_id="frc-1", tenant_id=TEST_TENANT_ID, overall=4.0)
    db.commit()

    repo = StoryQualityRepository(db)

    assert repo.count_evaluated_since(None) == 3
    assert repo.count_evaluated_since(None, forced=False) == 2
    assert repo.count_evaluated_since(None, forced=True) == 1
