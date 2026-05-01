"""Unit tests for StoryQualityRepository bucket aggregation.

These cover the new `forced=` filter on the existing `avg_overall_since` /
`count_evaluated_since` methods, plus the `summary_since` triple-bucket query.
"""
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
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


def _seed_story(
    db,
    *,
    story_id: str,
    tenant_id: str,
    entity_not_found: bool,
    was_forced: bool = False,
) -> UserStory:
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
        was_forced=was_forced,
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
    completeness: float | None = None,
    specificity: float | None = None,
    feasibility: float | None = None,
    risk_coverage: float | None = None,
    language_consistency: float | None = None,
) -> StoryQualityScore:
    score = StoryQualityScore(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        story_id=story_id,
        completeness=completeness if completeness is not None else overall,
        specificity=specificity if specificity is not None else overall,
        feasibility=feasibility if feasibility is not None else overall,
        risk_coverage=risk_coverage if risk_coverage is not None else overall,
        language_consistency=language_consistency if language_consistency is not None else overall,
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


def test_summary_since_returns_organic_dimension_averages():
    """The 5 judge dimensions must be averaged across organic stories only —
    forced rows have hard caps that would distort the per-dimension picture."""
    engine = _make_engine()
    db = sessionmaker(bind=engine)()

    # Two organic with custom per-dimension scores. risk_coverage is the
    # weakest in both — verifies it surfaces as such in the average.
    _seed_story(db, story_id="org-1", tenant_id=TEST_TENANT_ID, entity_not_found=False)
    _seed_score(
        db, story_id="org-1", tenant_id=TEST_TENANT_ID, overall=7.0,
        completeness=8.0, specificity=8.0, feasibility=8.0,
        risk_coverage=4.0, language_consistency=7.0,
    )
    _seed_story(db, story_id="org-2", tenant_id=TEST_TENANT_ID, entity_not_found=False)
    _seed_score(
        db, story_id="org-2", tenant_id=TEST_TENANT_ID, overall=7.5,
        completeness=9.0, specificity=8.0, feasibility=8.0,
        risk_coverage=5.0, language_consistency=7.5,
    )

    # Forced row with extreme dimensions — must NOT contaminate organic averages.
    _seed_story(db, story_id="frc-1", tenant_id=TEST_TENANT_ID, entity_not_found=True)
    _seed_score(
        db, story_id="frc-1", tenant_id=TEST_TENANT_ID, overall=2.0,
        completeness=1.0, specificity=1.0, feasibility=1.0,
        risk_coverage=1.0, language_consistency=1.0,
    )
    db.commit()

    summary = StoryQualityRepository(db).summary_since(None)
    organic = summary["organic"]

    assert organic["avg_completeness"] == pytest.approx(8.5)
    assert organic["avg_specificity"] == pytest.approx(8.0)
    assert organic["avg_feasibility"] == pytest.approx(8.0)
    assert organic["avg_risk_coverage"] == pytest.approx(4.5)
    assert organic["avg_language_consistency"] == pytest.approx(7.25)


def test_summary_since_dimension_averages_none_when_organic_empty():
    """No organic stories ⇒ all 5 dimension averages are None (not 0)."""
    engine = _make_engine()
    db = sessionmaker(bind=engine)()

    _seed_story(db, story_id="frc-1", tenant_id=TEST_TENANT_ID, entity_not_found=True)
    _seed_score(db, story_id="frc-1", tenant_id=TEST_TENANT_ID, overall=4.0)
    db.commit()

    organic = StoryQualityRepository(db).summary_since(None)["organic"]

    assert organic["count"] == 0
    assert organic["avg_completeness"] is None
    assert organic["avg_specificity"] is None
    assert organic["avg_feasibility"] is None
    assert organic["avg_risk_coverage"] is None
    assert organic["avg_language_consistency"] is None


def test_summary_since_subdivides_forced_by_was_forced():
    """Inside the forced bucket, creation_bypass_count vs override_count must
    partition correctly by `user_stories.was_forced`."""
    engine = _make_engine()
    db = sessionmaker(bind=engine)()

    # Organic baseline.
    _seed_story(db, story_id="org-1", tenant_id=TEST_TENANT_ID, entity_not_found=False)
    _seed_score(db, story_id="org-1", tenant_id=TEST_TENANT_ID, overall=8.0)

    # Creation bypass: entity not found, system bypassed via creation verb.
    _seed_story(
        db, story_id="creation-1", tenant_id=TEST_TENANT_ID,
        entity_not_found=True, was_forced=False,
    )
    _seed_score(db, story_id="creation-1", tenant_id=TEST_TENANT_ID, overall=5.0)

    # User explicit override.
    _seed_story(
        db, story_id="override-1", tenant_id=TEST_TENANT_ID,
        entity_not_found=True, was_forced=True,
    )
    _seed_score(db, story_id="override-1", tenant_id=TEST_TENANT_ID, overall=4.0)
    db.commit()

    summary = StoryQualityRepository(db).summary_since(None)

    assert summary["organic"]["count"] == 1
    assert summary["organic"]["avg_overall"] == 8.0

    assert summary["forced"]["count"] == 2
    assert summary["forced"]["avg_overall"] == 4.5
    assert summary["forced"]["creation_bypass_count"] == 1
    assert summary["forced"]["override_count"] == 1

    assert summary["all"]["count"] == 3
    # (8 + 5 + 4) / 3
    assert summary["all"]["avg_overall"] == pytest.approx(17.0 / 3.0)


def test_summary_since_forced_subcounts_zero_when_no_forced_rows():
    engine = _make_engine()
    db = sessionmaker(bind=engine)()

    _seed_story(db, story_id="org-1", tenant_id=TEST_TENANT_ID, entity_not_found=False)
    _seed_score(db, story_id="org-1", tenant_id=TEST_TENANT_ID, overall=7.0)
    db.commit()

    summary = StoryQualityRepository(db).summary_since(None)

    assert summary["forced"]["count"] == 0
    assert summary["forced"]["creation_bypass_count"] == 0
    assert summary["forced"]["override_count"] == 0


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
