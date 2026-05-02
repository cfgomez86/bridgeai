"""Unit tests for StoryFeedbackRepository — including cross-tenant isolation."""
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.context import current_tenant_id
from app.database.session import Base
from app.models.story_feedback import StoryFeedback
from app.models.user_story import UserStory
from app.repositories.story_feedback_repository import StoryFeedbackRepository
from tests.unit.conftest import TEST_TENANT_ID, TEST_USER_ID, TEST_CONNECTION_ID

TENANT_B = "test-tenant-00000000-0000-0000-0000-000000000099"
STORY_A = "story-tenant-a-001"
STORY_B = "story-tenant-b-001"


def _make_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


def _make_story(story_id: str, tenant_id: str) -> UserStory:
    return UserStory(
        id=story_id,
        tenant_id=tenant_id,
        source_connection_id=TEST_CONNECTION_ID,
        requirement_id=f"req-{story_id}",
        impact_analysis_id=f"ana-{story_id}",
        project_id="proj-x",
        title=f"Story for tenant {tenant_id[-4:]}",
        story_description="description",
        acceptance_criteria=json.dumps(["AC1"]),
        subtasks=json.dumps({"frontend": [], "backend": [{"title": "T", "description": "D"}], "configuration": []}),
        definition_of_done=json.dumps(["DoD1"]),
        risk_notes=json.dumps([]),
        story_points=1,
        risk_level="LOW",
        generation_time_seconds=0.1,
        created_at=datetime.now(timezone.utc),
    )


def _make_feedback(story_id: str, tenant_id: str, user_id: str = TEST_USER_ID) -> StoryFeedback:
    return StoryFeedback(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        story_id=story_id,
        user_id=user_id,
        rating="thumbs_up",
        comment=f"Comment from {tenant_id[-4:]}",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_list_with_comments_does_not_leak_other_tenant_feedback():
    """S-1: list_with_comments must filter by tenant_id and never expose other tenants' data."""
    engine = _make_engine()
    db = sessionmaker(bind=engine)()

    # Seed stories and feedback for two different tenants directly via ORM
    db.add(_make_story(STORY_A, TEST_TENANT_ID))
    db.add(_make_story(STORY_B, TENANT_B))
    db.add(_make_feedback(STORY_A, TEST_TENANT_ID))
    db.add(_make_feedback(STORY_B, TENANT_B))
    db.commit()

    # Query from tenant A's context (set by the autouse fixture in conftest.py)
    repo = StoryFeedbackRepository(db)
    results, total = repo.list_with_comments(limit=100, offset=0)

    story_ids = [fb.story_id for fb, _, _ in results]
    assert STORY_A in story_ids, "Tenant A's own feedback should be returned"
    assert STORY_B not in story_ids, "Tenant B's feedback must NOT appear in tenant A's results"


def test_list_with_comments_returns_own_tenant_data():
    """list_with_comments returns feedback belonging to the current tenant."""
    engine = _make_engine()
    db = sessionmaker(bind=engine)()

    db.add(_make_story(STORY_A, TEST_TENANT_ID))
    db.add(_make_feedback(STORY_A, TEST_TENANT_ID))
    db.commit()

    repo = StoryFeedbackRepository(db)
    results, total = repo.list_with_comments(limit=100, offset=0)

    assert len(results) == 1
    assert total == 1
    fb, title, email = results[0]
    assert fb.story_id == STORY_A
    assert fb.tenant_id == TEST_TENANT_ID
    assert isinstance(title, str)


def test_list_with_comments_rating_filter_still_applies():
    """rating filter and tenant isolation both work together."""
    engine = _make_engine()
    db = sessionmaker(bind=engine)()

    db.add(_make_story(STORY_A, TEST_TENANT_ID))
    db.add(_make_story(STORY_B, TENANT_B))
    # Tenant A: thumbs_down
    fb_a = _make_feedback(STORY_A, TEST_TENANT_ID)
    fb_a.rating = "thumbs_down"
    db.add(fb_a)
    # Tenant B: thumbs_up — should never appear
    db.add(_make_feedback(STORY_B, TENANT_B))
    db.commit()

    repo = StoryFeedbackRepository(db)
    results, total = repo.list_with_comments(limit=100, offset=0, rating="thumbs_up")

    story_ids = [fb.story_id for fb, _, _ in results]
    assert STORY_B not in story_ids, "Tenant B's thumbs_up must not leak into tenant A's results"


def test_list_with_comments_empty_when_no_feedback_for_tenant():
    """If the current tenant has no feedback, result is empty even if other tenants do."""
    engine = _make_engine()
    db = sessionmaker(bind=engine)()

    db.add(_make_story(STORY_B, TENANT_B))
    db.add(_make_feedback(STORY_B, TENANT_B))
    db.commit()

    repo = StoryFeedbackRepository(db)
    results, total = repo.list_with_comments(limit=100, offset=0)

    assert results == [], "No feedback should be returned for a tenant with no data"
    assert total == 0, "Total count should be 0 for a tenant with no data"
