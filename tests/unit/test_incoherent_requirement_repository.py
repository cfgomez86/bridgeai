"""Unit tests for IncoherentRequirementRepository — multi-tenant isolation,
save/list, reason filtering."""
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.context import current_tenant_id
from app.database.session import Base
from app.repositories.incoherent_requirement_repository import IncoherentRequirementRepository
from tests.unit.conftest import TEST_TENANT_ID, TEST_USER_ID


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def repo(db):
    return IncoherentRequirementRepository(db)


def _record(rid: str, codes: list[str], text: str = "casa roja en la playa") -> dict:
    return {
        "id": rid,
        "user_id": TEST_USER_ID,
        "requirement_text": text,
        "requirement_text_hash": "h" + rid,
        "warning": "no es accionable",
        "reason_codes": json.dumps(codes),
        "project_id": "proj",
        "source_connection_id": "conn",
        "model_used": "claude-haiku-4-5",
    }


def test_save_persists_with_tenant_id_from_context(repo, db):
    repo.save(_record("r1", ["non_software_request"]))
    rows, total = repo.list_with_user(limit=10, offset=0)
    assert total == 1
    assert len(rows) == 1
    record, _email = rows[0]
    assert record.id == "r1"
    assert record.tenant_id == TEST_TENANT_ID
    assert record.user_id == TEST_USER_ID
    assert "non_software_request" in record.reason_codes


def test_list_filters_by_tenant(repo, db):
    repo.save(_record("r1", ["unintelligible"]))
    repo.save(_record("r2", ["conversational"]))

    # Cambia el contexto a otro tenant: no debe ver nada
    token = current_tenant_id.set("other-tenant-xxxx")
    try:
        rows, total = IncoherentRequirementRepository(db).list_with_user(limit=10, offset=0)
        assert total == 0
        assert rows == []
    finally:
        current_tenant_id.reset(token)


def test_list_paginates_with_total_count(repo):
    for i in range(5):
        repo.save(_record(f"r{i}", ["non_software_request"]))

    rows, total = repo.list_with_user(limit=2, offset=0)
    assert total == 5
    assert len(rows) == 2

    rows2, total2 = repo.list_with_user(limit=2, offset=2)
    assert total2 == 5
    assert len(rows2) == 2

    rows3, total3 = repo.list_with_user(limit=2, offset=4)
    assert total3 == 5
    assert len(rows3) == 1


def test_list_filters_by_reason_code(repo):
    repo.save(_record("r1", ["non_software_request"]))
    repo.save(_record("r2", ["conversational", "empty_intent"]))
    repo.save(_record("r3", ["unintelligible"]))

    rows, total = repo.list_with_user(limit=10, offset=0, reason="conversational")
    assert total == 1
    assert rows[0][0].id == "r2"

    rows, total = repo.list_with_user(limit=10, offset=0, reason="non_software_request")
    assert total == 1
    assert rows[0][0].id == "r1"


def test_list_orders_newest_first(repo):
    repo.save(_record("r1", ["unintelligible"]))
    repo.save(_record("r2", ["unintelligible"]))
    repo.save(_record("r3", ["unintelligible"]))

    rows, _total = repo.list_with_user(limit=10, offset=0)
    ids = [rec.id for rec, _email in rows]
    # El más reciente primero (r3 fue insertado al final)
    assert ids[0] == "r3"
