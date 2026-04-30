from datetime import datetime, timezone
from unittest.mock import MagicMock
import hashlib

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base
from app.domain.user_story import UserStory
from tests.unit.conftest import TEST_TENANT_ID, TEST_CONNECTION_ID, TEST_CONNECTION_ID_B
from app.models.requirement import Requirement
from app.models.impact_analysis import ImpactAnalysis
from app.repositories.code_file_repository import CodeFileRepository
from app.repositories.requirement_repository import RequirementRepository
from app.repositories.impact_analysis_repository import ImpactAnalysisRepository
from app.repositories.user_story_repository import UserStoryRepository
from app.services.ai_story_generator import AIStoryGenerator, HallucinatedPathError
from app.services.story_ai_provider import StoryAIProvider, StubStoryProvider
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
        code_file_repo=CodeFileRepository(db),
        settings=settings,
    ), db


def insert_requirement(
    db, req_id: str = "req-1", connection_id: str = TEST_CONNECTION_ID
) -> Requirement:
    text = "User registration with email"
    req = Requirement(
        id=req_id,
        tenant_id=TEST_TENANT_ID,
        source_connection_id=connection_id,
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


def insert_analysis(
    db, ana_id: str = "ana-1", connection_id: str = TEST_CONNECTION_ID
) -> ImpactAnalysis:
    analysis = ImpactAnalysis(
        id=ana_id,
        tenant_id=TEST_TENANT_ID,
        source_connection_id=connection_id,
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
    result, entity_not_found = svc.generate("req-1", "ana-1", "proj", TEST_CONNECTION_ID)
    assert isinstance(result, UserStory)
    assert entity_not_found is False


def test_generate_populates_all_fields():
    engine = make_engine()
    svc, db = make_service(engine)
    insert_requirement(db)
    insert_analysis(db)
    result, _ = svc.generate("req-1", "ana-1", "proj", TEST_CONNECTION_ID)
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
    result, _ = svc.generate("req-1", "ana-1", "proj", TEST_CONNECTION_ID)
    story_repo = UserStoryRepository(db)
    persisted = story_repo.find_by_id(result.story_id)
    assert persisted is not None
    assert persisted.id == result.story_id
    assert persisted.source_connection_id == TEST_CONNECTION_ID


def test_cache_hit_returns_without_calling_ai():
    engine = make_engine()
    svc, db = make_service(engine)
    insert_requirement(db)
    insert_analysis(db)
    first, _ = svc.generate("req-1", "ana-1", "proj", TEST_CONNECTION_ID)

    mock_provider = MagicMock(spec=StubStoryProvider)
    svc._generator._provider = mock_provider

    second, _ = svc.generate("req-1", "ana-1", "proj", TEST_CONNECTION_ID)
    mock_provider.generate_story.assert_not_called()
    assert second.story_id == first.story_id


def test_missing_requirement_raises_value_error():
    engine = make_engine()
    svc, db = make_service(engine)
    insert_analysis(db)
    with pytest.raises(ValueError, match="not found"):
        svc.generate("nonexistent-req", "ana-1", "proj", TEST_CONNECTION_ID)


def test_missing_analysis_raises_value_error():
    engine = make_engine()
    svc, db = make_service(engine)
    insert_requirement(db)
    with pytest.raises(ValueError, match="not found"):
        svc.generate("req-1", "nonexistent-ana", "proj", TEST_CONNECTION_ID)


def test_missing_connection_raises_value_error():
    engine = make_engine()
    svc, db = make_service(engine)
    insert_requirement(db)
    insert_analysis(db)
    with pytest.raises(ValueError, match="source_connection_id"):
        svc.generate("req-1", "ana-1", "proj", "")


def test_cross_connection_requirement_raises():
    """Una requirement del Repo A no puede combinarse con source_connection_id=RepoB."""
    engine = make_engine()
    svc, db = make_service(engine)
    # requirement está en conexión A, analysis también
    insert_requirement(db, "req-A", connection_id=TEST_CONNECTION_ID)
    insert_analysis(db, "ana-A", connection_id=TEST_CONNECTION_ID)
    # Pero generamos pidiendo conexión B
    with pytest.raises(ValueError, match="not found"):
        svc.generate("req-A", "ana-A", "proj", TEST_CONNECTION_ID_B)


def test_cross_connection_analysis_raises():
    """Combinar requirement de A con analysis de B debe fallar aunque ambos existan."""
    engine = make_engine()
    svc, db = make_service(engine)
    insert_requirement(db, "req-A", connection_id=TEST_CONNECTION_ID)
    insert_analysis(db, "ana-B", connection_id=TEST_CONNECTION_ID_B)
    # req-A existe en A, pero no en B → falla
    with pytest.raises(ValueError, match="not found"):
        svc.generate("req-A", "ana-B", "proj", TEST_CONNECTION_ID_B)


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


class _SequenceProvider(StoryAIProvider):
    """Provider que devuelve respuestas predefinidas en secuencia para testear retries."""

    def __init__(self, responses: list[dict]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    def generate_story(self, context: dict) -> dict:
        self.calls.append(dict(context))
        if not self._responses:
            raise AssertionError("No more responses queued")
        return self._responses.pop(0)


def _valid_story(subtasks: dict, risk_notes: list[str] | None = None) -> dict:
    return {
        "title": "T",
        "story_description": "Como X quiero Y para Z",
        "acceptance_criteria": [
            "Given X, When the action runs, Then the system returns the expected result.",
            "Given Y, When the user retries, Then no duplicate is created.",
            "Given Z, When the operation completes, Then an audit log entry is written.",
        ],
        "subtasks": subtasks,
        "definition_of_done": ["d1", "d2", "d3"],
        "risk_notes": risk_notes if risk_notes is not None else [],
    }


def _sub(title: str, description: str = "Detailed steps to complete this task.") -> dict:
    return {"title": title, "description": description}


def test_generator_detects_hallucinated_path_and_retries():
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=2)

    hallucinated = _valid_story(
        {
            "frontend": [],
            "backend": [
                _sub("Agregar endpoint en app/api/routes/products.py"),
                _sub("Actualizar NotificationService.java"),
            ],
            "configuration": [],
        }
    )
    clean = _valid_story(
        {
            "frontend": [],
            "backend": [_sub("Actualizar NotificationService.java")],
            "configuration": [],
        }
    )
    provider = _SequenceProvider([hallucinated, clean])
    gen = AIStoryGenerator(provider, settings)

    result = gen.generate(
        {"available_file_paths": ["NotificationService.java"]}
    )

    assert len(provider.calls) == 2
    assert provider.calls[1].get("hallucinated_last_attempt") == [
        "app/api/routes/products.py"
    ]
    backend_titles = [item["title"] for item in result["subtasks"]["backend"]]
    assert backend_titles == ["Actualizar NotificationService.java"]


def test_generator_strips_invalid_paths_after_max_retries():
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=1)

    hallucinated = _valid_story(
        {
            "frontend": [],
            "backend": [
                _sub("Agregar endpoint en app/api/routes/products.py"),
                _sub("Actualizar NotificationService.java"),
            ],
            "configuration": [],
        }
    )
    provider = _SequenceProvider([hallucinated, hallucinated])
    gen = AIStoryGenerator(provider, settings)

    result = gen.generate({"available_file_paths": ["NotificationService.java"]})

    backend_texts = " ".join(
        f"{item['title']} {item['description']}" for item in result["subtasks"]["backend"]
    )
    assert "app/api/routes/products.py" not in backend_texts
    assert "NotificationService.java" in backend_texts


def test_generator_empty_whitelist_rejects_any_path():
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=0)

    bad = _valid_story(
        {
            "frontend": [],
            "backend": [_sub("Editar src/Foo.java")],
            "configuration": [],
        }
    )
    provider = _SequenceProvider([bad])
    gen = AIStoryGenerator(provider, settings)

    result = gen.generate({"available_file_paths": []})
    backend_texts = " ".join(
        f"{item['title']} {item['description']}" for item in result["subtasks"]["backend"]
    )
    assert "src/Foo.java" not in backend_texts


def test_generator_accepts_paths_in_whitelist():
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=0)
    resp = _valid_story(
        {
            "frontend": [],
            "backend": [_sub("Actualizar app/services/X.py")],
            "configuration": [],
        }
    )
    provider = _SequenceProvider([resp])
    gen = AIStoryGenerator(provider, settings)

    result = gen.generate({"available_file_paths": ["app/services/X.py"]})
    backend_titles = [item["title"] for item in result["subtasks"]["backend"]]
    assert backend_titles == ["Actualizar app/services/X.py"]


def test_hallucinated_path_error_carries_paths():
    err = HallucinatedPathError(["a/b.py", "c/d.ts"])
    assert err.invalid_paths == ["a/b.py", "c/d.ts"]


def test_build_whitelist_under_cap_returns_all():
    all_paths = {"a.java", "b.java", "c.java"}
    result = StoryGenerationService._build_whitelist(all_paths, [], cap=10)
    assert result == ["a.java", "b.java", "c.java"]


def test_build_whitelist_prioritizes_impacted_and_siblings():
    all_paths = {
        "src/NotificationService.java",
        "src/OtherService.java",
        "src/unrelated/Helper.java",
        "docs/readme.md",
    }
    result = StoryGenerationService._build_whitelist(
        all_paths, ["src/NotificationService.java"], cap=3
    )
    assert "src/NotificationService.java" in result
    assert "src/OtherService.java" in result
    assert len(result) == 3


# ---------------------------------------------------------------------------
# Entity existence validation
# ---------------------------------------------------------------------------

from app.services.entity_existence_checker import (
    EntityCheckResult,
    EntityExistenceChecker,
    EntityNotFoundError,
)


def make_service_with_checker(engine, checker, validation_mode: str = "warn"):
    db = sessionmaker(bind=engine)()
    from app.core.config import Settings
    settings = Settings(
        DATABASE_URL="sqlite:///:memory:",
        AI_MAX_RETRIES=2,
        ENTITY_VALIDATION_MODE=validation_mode,
    )
    return StoryGenerationService(
        ai_generator=AIStoryGenerator(StubStoryProvider(), settings),
        requirement_repo=RequirementRepository(db),
        impact_repo=ImpactAnalysisRepository(db),
        story_repo=UserStoryRepository(db),
        points_calculator=StoryPointsCalculator(),
        code_file_repo=CodeFileRepository(db),
        settings=settings,
        entity_checker=checker,
    ), db


def insert_requirement_custom(
    db, *, action: str = "update", feature_type: str = "bugfix", entity: str = "Product",
):
    text = "Some requirement"
    req = Requirement(
        id="req-1",
        tenant_id=TEST_TENANT_ID,
        source_connection_id=TEST_CONNECTION_ID,
        requirement_text=text,
        requirement_text_hash=hashlib.sha256(text.encode()).hexdigest(),
        project_id="proj",
        intent="x",
        action=action,
        entity=entity,
        feature_type=feature_type,
        priority="medium",
        business_domain="user_management",
        technical_scope="backend",
        estimated_complexity="MEDIUM",
        keywords='[]',
        processing_time_seconds=1.0,
        created_at=datetime.now(timezone.utc),
    )
    db.add(req)
    db.commit()


def test_entity_not_found_blocks_without_force():
    engine = make_engine()
    checker = MagicMock(spec=EntityExistenceChecker)
    checker.check.return_value = EntityCheckResult(
        entity="Product", found=False, matched_files=[],
        suggestions=["ProductModel"],
    )
    svc, db = make_service_with_checker(engine, checker)
    insert_requirement_custom(db, action="update", feature_type="bugfix")
    insert_analysis(db)
    with pytest.raises(EntityNotFoundError) as exc_info:
        svc.generate("req-1", "ana-1", "proj", TEST_CONNECTION_ID)
    assert exc_info.value.entity == "Product"
    assert exc_info.value.suggestions == ["ProductModel"]


def test_entity_not_found_proceeds_with_force():
    engine = make_engine()
    checker = MagicMock(spec=EntityExistenceChecker)
    checker.check.return_value = EntityCheckResult(
        entity="Product", found=False, matched_files=[], suggestions=[],
    )
    svc, db = make_service_with_checker(engine, checker)
    insert_requirement_custom(db, action="update", feature_type="bugfix")
    insert_analysis(db)
    story, entity_not_found = svc.generate(
        "req-1", "ana-1", "proj", TEST_CONNECTION_ID, force=True
    )
    assert entity_not_found is True
    assert story.story_id


def test_entity_not_found_proceeds_for_intentional_creation():
    engine = make_engine()
    checker = MagicMock(spec=EntityExistenceChecker)
    checker.check.return_value = EntityCheckResult(
        entity="Product", found=False, matched_files=[], suggestions=[],
    )
    svc, db = make_service_with_checker(engine, checker)
    insert_requirement_custom(db, action="create", feature_type="feature")
    insert_analysis(db)
    story, entity_not_found = svc.generate(
        "req-1", "ana-1", "proj", TEST_CONNECTION_ID
    )
    assert entity_not_found is True
    assert story.story_id


def test_entity_found_proceeds_normally():
    engine = make_engine()
    checker = MagicMock(spec=EntityExistenceChecker)
    checker.check.return_value = EntityCheckResult(
        entity="Product", found=True, matched_files=["a.py"], suggestions=[],
    )
    svc, db = make_service_with_checker(engine, checker)
    insert_requirement_custom(db, action="update", feature_type="bugfix")
    insert_analysis(db)
    story, entity_not_found = svc.generate(
        "req-1", "ana-1", "proj", TEST_CONNECTION_ID
    )
    assert entity_not_found is False
    assert story.story_id


def test_entity_validation_mode_off_skips_checker():
    engine = make_engine()
    checker = MagicMock(spec=EntityExistenceChecker)
    svc, db = make_service_with_checker(engine, checker, validation_mode="off")
    insert_requirement_custom(db, action="update", feature_type="bugfix")
    insert_analysis(db)
    story, entity_not_found = svc.generate(
        "req-1", "ana-1", "proj", TEST_CONNECTION_ID
    )
    checker.check.assert_not_called()
    assert entity_not_found is False
    assert story.story_id
