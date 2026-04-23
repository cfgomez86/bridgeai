from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base
from app.models.user_story import UserStory
from app.repositories.user_story_repository import UserStoryRepository
from tests.unit.conftest import TEST_CONNECTION_ID, TEST_CONNECTION_ID_B


def make_repo():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    return UserStoryRepository(db)


def make_story(
    story_id: str = "story-1",
    requirement_id: str = "req-1",
    analysis_id: str = "ana-1",
    project_id: str = "proj-a",
) -> UserStory:
    return UserStory(
        id=story_id,
        requirement_id=requirement_id,
        impact_analysis_id=analysis_id,
        project_id=project_id,
        title="Test Story",
        story_description="As a user, I want to test so that coverage is met.",
        acceptance_criteria='["Criterion 1"]',
        subtasks='{"frontend": [], "backend": ["Task 1"], "configuration": []}',
        definition_of_done='["Done 1"]',
        risk_notes='[]',
        story_points=3,
        risk_level="LOW",
        generation_time_seconds=0.5,
        created_at=datetime.now(timezone.utc),
    )


def test_save_inserts_record():
    repo = make_repo()
    saved = repo.save(make_story(), TEST_CONNECTION_ID)
    assert saved.id == "story-1"
    assert saved.source_connection_id == TEST_CONNECTION_ID


def test_find_by_id_returns_saved_record():
    repo = make_repo()
    repo.save(make_story("story-abc"), TEST_CONNECTION_ID)
    found = repo.find_by_id("story-abc")
    assert found is not None
    assert found.id == "story-abc"
    assert found.story_points == 3


def test_find_by_id_returns_none_for_missing():
    repo = make_repo()
    assert repo.find_by_id("nonexistent") is None


def test_find_by_id_scoped_filters_by_connection():
    repo = make_repo()
    repo.save(make_story("story-abc"), TEST_CONNECTION_ID)
    assert repo.find_by_id_scoped("story-abc", TEST_CONNECTION_ID) is not None
    assert repo.find_by_id_scoped("story-abc", TEST_CONNECTION_ID_B) is None


def test_find_by_requirement_and_analysis_returns_story():
    repo = make_repo()
    repo.save(
        make_story("s1", requirement_id="req-x", analysis_id="ana-x"),
        TEST_CONNECTION_ID,
    )
    found = repo.find_by_requirement_and_analysis("req-x", "ana-x", TEST_CONNECTION_ID)
    assert found is not None
    assert found.id == "s1"


def test_find_by_requirement_and_analysis_scoped_by_connection():
    repo = make_repo()
    repo.save(
        make_story("s1", requirement_id="req-x", analysis_id="ana-x"),
        TEST_CONNECTION_ID,
    )
    # Otra conexión: aunque req_id y analysis_id coincidan (ficticio), no debe hallarlo
    assert repo.find_by_requirement_and_analysis(
        "req-x", "ana-x", TEST_CONNECTION_ID_B
    ) is None


def test_find_by_requirement_and_analysis_returns_none_if_missing():
    repo = make_repo()
    assert repo.find_by_requirement_and_analysis("req-x", "ana-x", TEST_CONNECTION_ID) is None


def test_find_by_requirement_and_analysis_does_not_match_partial():
    repo = make_repo()
    repo.save(
        make_story("s1", requirement_id="req-x", analysis_id="ana-x"),
        TEST_CONNECTION_ID,
    )
    assert repo.find_by_requirement_and_analysis(
        "req-x", "ana-OTHER", TEST_CONNECTION_ID
    ) is None
