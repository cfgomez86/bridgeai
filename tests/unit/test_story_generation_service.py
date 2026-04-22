from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base
from app.domain.user_story import UserStory
from tests.unit.conftest import TEST_TENANT_ID
from app.models.requirement import Requirement
from app.models.impact_analysis import ImpactAnalysis
from app.repositories.requirement_repository import RequirementRepository
from app.repositories.impact_analysis_repository import ImpactAnalysisRepository
from app.repositories.user_story_repository import UserStoryRepository
from app.services.ai_story_generator import AIStoryGenerator
from app.services.story_ai_provider import StubStoryProvider
from app.services.story_generation_service import StoryGenerationService
from app.services.story_points_calculator import StoryPointsCalculator


def make_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


def make_service(engine):
    db = sessionmaker(bind=engine)()
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=2)
    return StoryGenerationService(
        ai_generator=AIStoryGenerator(StubStoryProvider(), settings),
        requirement_repo=RequirementRepository(db),
        impact_repo=ImpactAnalysisRepository(db),
        story_repo=UserStoryRepository(db),
        points_calculator=StoryPointsCalculator(),
        settings=settings,
    ), db


def insert_requirement(db, req_id: str = "req-1") -> Requirement:
    import hashlib
    text = "User registration with email"
    req = Requirement(
        id=req_id,
        tenant_id=TEST_TENANT_ID,
        requirement_text=text,
        requirement_text_hash=hashlib.sha256(text.encode()).hexdigest(),
        project_id="proj",
        intent="create_user_account",
        action="create",
        entity="user",
        feature_type="feature",
        priority="medium",
        business_domain="user_management",
        technical_scope="backend",
        estimated_complexity="MEDIUM",
        keywords='["user", "email"]',
        processing_time_seconds=1.0,
        created_at=datetime.now(timezone.utc),
    )
    db.add(req)
    db.commit()
    return req


def insert_analysis(db, ana_id: str = "ana-1") -> ImpactAnalysis:
    analysis = ImpactAnalysis(
        id=ana_id,
        tenant_id=TEST_TENANT_ID,
        requirement="User registration with email",
        risk_level="LOW",
        files_impacted=2,
        modules_impacted=1,
        analysis_summary="Two files impacted",
        created_at=datetime.now(timezone.utc),
    )
    db.add(analysis)
    db.commit()
    return analysis


def test_generate_returns_user_story():
    engine = make_engine()
    svc, db = make_service(engine)
    insert_requirement(db)
    insert_analysis(db)
    result = svc.generate("req-1", "ana-1", "proj")
    assert isinstance(result, UserStory)


def test_generate_populates_all_fields():
    engine = make_engine()
    svc, db = make_service(engine)
    insert_requirement(db)
    insert_analysis(db)
    result = svc.generate("req-1", "ana-1", "proj")
    assert result.story_id
    assert result.title
    assert result.story_description
    assert len(result.acceptance_criteria) >= 1
    assert isinstance(result.subtasks, dict)
    assert any(result.subtasks.get(c) for c in ("frontend", "backend", "configuration"))
    assert result.story_points >= 1
    assert result.risk_level == "LOW"


def test_generate_persists_story():
    engine = make_engine()
    svc, db = make_service(engine)
    insert_requirement(db)
    insert_analysis(db)
    result = svc.generate("req-1", "ana-1", "proj")
    story_repo = UserStoryRepository(db)
    persisted = story_repo.find_by_id(result.story_id)
    assert persisted is not None
    assert persisted.id == result.story_id


def test_cache_hit_returns_without_calling_ai():
    engine = make_engine()
    svc, db = make_service(engine)
    insert_requirement(db)
    insert_analysis(db)
    first = svc.generate("req-1", "ana-1", "proj")

    # Replace provider with a mock that should NOT be called
    mock_provider = MagicMock(spec=StubStoryProvider)
    svc._generator._provider = mock_provider

    second = svc.generate("req-1", "ana-1", "proj")
    mock_provider.generate_story.assert_not_called()
    assert second.story_id == first.story_id


def test_missing_requirement_raises_value_error():
    engine = make_engine()
    svc, db = make_service(engine)
    insert_analysis(db)
    with pytest.raises(ValueError, match="not found"):
        svc.generate("nonexistent-req", "ana-1", "proj")


def test_missing_analysis_raises_value_error():
    engine = make_engine()
    svc, db = make_service(engine)
    insert_requirement(db)
    with pytest.raises(ValueError, match="not found"):
        svc.generate("req-1", "nonexistent-ana", "proj")


def test_story_points_low_complexity():
    calc = StoryPointsCalculator()
    assert calc.calculate("LOW", 1, "LOW") == 2


def test_story_points_medium_complexity():
    calc = StoryPointsCalculator()
    assert calc.calculate("MEDIUM", 5, "LOW") == 5


def test_story_points_high_complexity():
    calc = StoryPointsCalculator()
    points = calc.calculate("HIGH", 4, "LOW")
    assert 8 <= points <= 13


def test_story_points_high_risk_overrides_low_complexity():
    calc = StoryPointsCalculator()
    points = calc.calculate("LOW", 1, "HIGH")
    assert 8 <= points <= 13
