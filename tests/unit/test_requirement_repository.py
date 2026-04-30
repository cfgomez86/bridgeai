from datetime import datetime, timezone
import hashlib

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base
from app.repositories.requirement_repository import RequirementRepository
from tests.unit.conftest import TEST_CONNECTION_ID, TEST_CONNECTION_ID_B


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


def make_requirement(
    req_id: str = "test-id-1",
    project_id: str = "proj-a",
    text: str = "Add user registration",
) -> dict:
    return {
        "id": req_id,
        "requirement_text": text,
        "requirement_text_hash": hashlib.sha256(text.encode()).hexdigest(),
        "project_id": project_id,
        "intent": "create_user_account",
        "action": "create",
        "entity": "user",
        "feature_type": "feature",
        "priority": "medium",
        "business_domain": "user_management",
        "technical_scope": "backend",
        "estimated_complexity": "MEDIUM",
        "keywords": '["user", "registration"]',
        "processing_time_seconds": 0.5,
        "created_at": datetime.now(timezone.utc),
    }


def test_save_inserts_record():
    repo = make_repo()
    saved = repo.save(make_requirement(), TEST_CONNECTION_ID)
    assert saved.id == "test-id-1"
    assert saved.source_connection_id == TEST_CONNECTION_ID


def test_find_by_id_returns_saved_record():
    repo = make_repo()
    repo.save(make_requirement("uuid-abc"), TEST_CONNECTION_ID)
    found = repo.find_by_id("uuid-abc", TEST_CONNECTION_ID)
    assert found is not None
    assert found.id == "uuid-abc"
    assert found.project_id == "proj-a"


def test_find_by_id_returns_none_for_missing():
    repo = make_repo()
    assert repo.find_by_id("nonexistent", TEST_CONNECTION_ID) is None


def test_find_by_id_is_scoped_to_connection():
    repo = make_repo()
    repo.save(make_requirement("uuid-abc"), TEST_CONNECTION_ID)
    # Otra conexión del mismo tenant no debe ver la requirement
    assert repo.find_by_id("uuid-abc", TEST_CONNECTION_ID_B) is None


def test_list_by_project_returns_project_records():
    repo = make_repo()
    repo.save(make_requirement("id-1", "proj-x"), TEST_CONNECTION_ID)
    repo.save(make_requirement("id-2", "proj-x", text="otra"), TEST_CONNECTION_ID)
    repo.save(make_requirement("id-3", "proj-y"), TEST_CONNECTION_ID)
    results = repo.list_by_project("proj-x", TEST_CONNECTION_ID)
    assert len(results) == 2
    assert all(r.project_id == "proj-x" for r in results)


def test_list_by_project_is_scoped_to_connection():
    repo = make_repo()
    repo.save(make_requirement("id-1", "proj-x"), TEST_CONNECTION_ID)
    repo.save(make_requirement("id-2", "proj-x", text="otra"), TEST_CONNECTION_ID_B)
    results_a = repo.list_by_project("proj-x", TEST_CONNECTION_ID)
    results_b = repo.list_by_project("proj-x", TEST_CONNECTION_ID_B)
    assert [r.id for r in results_a] == ["id-1"]
    assert [r.id for r in results_b] == ["id-2"]


def test_find_by_text_project_and_connection_is_cache_key():
    repo = make_repo()
    req_a = make_requirement("id-a", "proj", text="mismo texto")
    req_b = make_requirement("id-b", "proj", text="mismo texto")
    repo.save(req_a, TEST_CONNECTION_ID)
    repo.save(req_b, TEST_CONNECTION_ID_B)
    text_hash = hashlib.sha256(b"mismo texto").hexdigest()
    found_a = repo.find_by_text_project_and_connection(text_hash, "proj", TEST_CONNECTION_ID)
    found_b = repo.find_by_text_project_and_connection(text_hash, "proj", TEST_CONNECTION_ID_B)
    assert found_a is not None and found_a.id == "id-a"
    assert found_b is not None and found_b.id == "id-b"
