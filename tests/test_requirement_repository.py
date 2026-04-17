from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base
from app.models.requirement import Requirement
from app.repositories.requirement_repository import RequirementRepository


def make_repo():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    return RequirementRepository(db)


def make_requirement(req_id: str = "test-id-1", project_id: str = "proj-a") -> Requirement:
    return Requirement(
        id=req_id,
        requirement_text="Add user registration",
        project_id=project_id,
        intent="create_user_account",
        action="create",
        entity="user",
        feature_type="feature",
        priority="medium",
        business_domain="user_management",
        technical_scope="backend",
        estimated_complexity="MEDIUM",
        keywords='["user", "registration"]',
        processing_time_seconds=0.5,
        created_at=datetime.now(timezone.utc),
    )


def test_save_inserts_record():
    repo = make_repo()
    req = make_requirement()
    saved = repo.save(req)
    assert saved.id == "test-id-1"


def test_find_by_id_returns_saved_record():
    repo = make_repo()
    repo.save(make_requirement("uuid-abc"))
    found = repo.find_by_id("uuid-abc")
    assert found is not None
    assert found.id == "uuid-abc"
    assert found.project_id == "proj-a"


def test_find_by_id_returns_none_for_missing():
    repo = make_repo()
    assert repo.find_by_id("nonexistent") is None


def test_list_by_project_returns_project_records():
    repo = make_repo()
    repo.save(make_requirement("id-1", "proj-x"))
    repo.save(make_requirement("id-2", "proj-x"))
    repo.save(make_requirement("id-3", "proj-y"))
    results = repo.list_by_project("proj-x")
    assert len(results) == 2
    assert all(r.project_id == "proj-x" for r in results)


def test_list_by_project_excludes_other_projects():
    repo = make_repo()
    repo.save(make_requirement("id-1", "proj-a"))
    repo.save(make_requirement("id-2", "proj-b"))
    results = repo.list_by_project("proj-b")
    assert len(results) == 1
    assert results[0].id == "id-2"
