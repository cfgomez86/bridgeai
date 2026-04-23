"""
Aislamiento cross-repo dentro del mismo tenant.

Verifica que Requirement, ImpactAnalysis y UserStory generados para una
source_connection_id no sean visibles a queries scopeadas a otra
source_connection_id, aun dentro del mismo tenant.
"""
import hashlib
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base
from app.models.impact_analysis import ImpactAnalysis, ImpactedFile
from app.models.requirement import Requirement
from app.models.user_story import UserStory
from app.repositories.impact_analysis_repository import ImpactAnalysisRepository
from app.repositories.requirement_repository import RequirementRepository
from app.repositories.user_story_repository import UserStoryRepository
from tests.unit.conftest import (
    TEST_CONNECTION_ID,
    TEST_CONNECTION_ID_B,
    TEST_TENANT_ID,
)


def _make_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _req(req_id: str, connection_id: str, text: str = "add login") -> Requirement:
    return Requirement(
        id=req_id,
        tenant_id=TEST_TENANT_ID,
        source_connection_id=connection_id,
        requirement_text=text,
        requirement_text_hash=hashlib.sha256(text.encode()).hexdigest(),
        project_id="proj",
        intent="intent",
        action="action",
        entity="entity",
        feature_type="feature",
        priority="medium",
        business_domain="domain",
        technical_scope="backend",
        estimated_complexity="MEDIUM",
        keywords="[]",
        processing_time_seconds=0.1,
        created_at=datetime.now(timezone.utc),
    )


def _analysis(ana_id: str, connection_id: str) -> ImpactAnalysis:
    return ImpactAnalysis(
        id=ana_id,
        tenant_id=TEST_TENANT_ID,
        source_connection_id=connection_id,
        requirement="r",
        risk_level="LOW",
        files_impacted=1,
        modules_impacted=1,
        analysis_summary="s",
        created_at=datetime.now(timezone.utc),
    )


def _story(
    story_id: str, requirement_id: str, analysis_id: str, connection_id: str
) -> UserStory:
    return UserStory(
        id=story_id,
        tenant_id=TEST_TENANT_ID,
        source_connection_id=connection_id,
        requirement_id=requirement_id,
        impact_analysis_id=analysis_id,
        project_id="proj",
        language="es",
        title="t",
        story_description="d",
        acceptance_criteria='["a"]',
        subtasks='{"frontend": [], "backend": [], "configuration": []}',
        definition_of_done='["d"]',
        risk_notes="[]",
        story_points=3,
        risk_level="LOW",
        generation_time_seconds=0.1,
        created_at=datetime.now(timezone.utc),
    )


def test_requirement_isolation_between_connections():
    db = _make_db()
    db.add(_req("req-A", TEST_CONNECTION_ID))
    db.add(_req("req-B", TEST_CONNECTION_ID_B))
    db.commit()
    repo = RequirementRepository(db)

    assert repo.find_by_id("req-A", TEST_CONNECTION_ID) is not None
    assert repo.find_by_id("req-A", TEST_CONNECTION_ID_B) is None
    assert repo.find_by_id("req-B", TEST_CONNECTION_ID_B) is not None
    assert repo.find_by_id("req-B", TEST_CONNECTION_ID) is None


def test_requirement_cache_hit_is_per_connection():
    """Mismo texto en dos repos genera dos requirements distintos."""
    db = _make_db()
    db.add(_req("req-A", TEST_CONNECTION_ID, text="agregar login"))
    db.add(_req("req-B", TEST_CONNECTION_ID_B, text="agregar login"))
    db.commit()
    repo = RequirementRepository(db)
    text_hash = hashlib.sha256(b"agregar login").hexdigest()

    found_a = repo.find_by_text_project_and_connection(text_hash, "proj", TEST_CONNECTION_ID)
    found_b = repo.find_by_text_project_and_connection(text_hash, "proj", TEST_CONNECTION_ID_B)
    assert found_a is not None and found_a.id == "req-A"
    assert found_b is not None and found_b.id == "req-B"
    assert found_a.id != found_b.id


def test_impact_analysis_isolation_between_connections():
    db = _make_db()
    db.add(_analysis("ana-A", TEST_CONNECTION_ID))
    db.add(_analysis("ana-B", TEST_CONNECTION_ID_B))
    db.commit()
    repo = ImpactAnalysisRepository(db)

    assert repo.find_by_id("ana-A", TEST_CONNECTION_ID) is not None
    assert repo.find_by_id("ana-A", TEST_CONNECTION_ID_B) is None
    assert repo.find_by_id("ana-B", TEST_CONNECTION_ID_B) is not None


def test_impacted_files_isolation_between_connections():
    db = _make_db()
    db.add(_analysis("ana-A", TEST_CONNECTION_ID))
    db.add(_analysis("ana-B", TEST_CONNECTION_ID_B))
    db.add(
        ImpactedFile(
            analysis_id="ana-A",
            tenant_id=TEST_TENANT_ID,
            source_connection_id=TEST_CONNECTION_ID,
            file_path="a.py",
            reason="keyword_match",
        )
    )
    db.add(
        ImpactedFile(
            analysis_id="ana-B",
            tenant_id=TEST_TENANT_ID,
            source_connection_id=TEST_CONNECTION_ID_B,
            file_path="b.py",
            reason="keyword_match",
        )
    )
    db.commit()
    repo = ImpactAnalysisRepository(db)

    paths_a = repo.find_file_paths("ana-A", TEST_CONNECTION_ID)
    paths_b = repo.find_file_paths("ana-B", TEST_CONNECTION_ID_B)
    cross_a = repo.find_file_paths("ana-A", TEST_CONNECTION_ID_B)
    cross_b = repo.find_file_paths("ana-B", TEST_CONNECTION_ID)

    assert paths_a == ["a.py"]
    assert paths_b == ["b.py"]
    assert cross_a == []  # Repo A's files invisible from Repo B context
    assert cross_b == []


def test_story_isolation_between_connections():
    db = _make_db()
    db.add(_story("s-A", "req-A", "ana-A", TEST_CONNECTION_ID))
    db.add(_story("s-B", "req-B", "ana-B", TEST_CONNECTION_ID_B))
    db.commit()
    repo = UserStoryRepository(db)

    assert repo.find_by_id_scoped("s-A", TEST_CONNECTION_ID) is not None
    assert repo.find_by_id_scoped("s-A", TEST_CONNECTION_ID_B) is None
    # find_by_requirement_and_analysis también debe respetar el scope
    assert repo.find_by_requirement_and_analysis("req-A", "ana-A", TEST_CONNECTION_ID) is not None
    assert repo.find_by_requirement_and_analysis("req-A", "ana-A", TEST_CONNECTION_ID_B) is None
