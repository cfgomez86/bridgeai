"""Integration tests for GET /api/v1/admin/incoherent-requirements."""
import json
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.core.context import current_tenant_id, current_user_id
from app.database.session import Base, get_db
from app.main import create_app
from app.models.incoherent_requirement import IncoherentRequirement
from app.models.user import User
from tests.integration.auth_helpers import (
    TEST_TENANT_ID,
    TEST_USER_ID,
)


def _seed_record(
    db,
    rid: str,
    tenant_id: str = TEST_TENANT_ID,
    user_id: str = TEST_USER_ID,
    codes: list[str] | None = None,
    text: str = "absurdo",
) -> None:
    db.add(
        IncoherentRequirement(
            id=rid,
            tenant_id=tenant_id,
            user_id=user_id,
            requirement_text=text,
            requirement_text_hash="h" + rid,
            warning="not actionable",
            reason_codes=json.dumps(codes or ["non_software_request"]),
            project_id="p",
            source_connection_id="c",
            model_used="claude-haiku-4-5",
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()


def make_client(role: str = "admin") -> tuple[TestClient, sessionmaker]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    async def mock_auth() -> User:
        current_tenant_id.set(TEST_TENANT_ID)
        current_user_id.set(TEST_USER_ID)
        return User(
            id=TEST_USER_ID,
            auth0_user_id="auth0|test_user",
            tenant_id=TEST_TENANT_ID,
            email="admin@bridgeai.test",
            name="Admin",
            role=role,
            created_at=datetime.utcnow(),
        )

    app = create_app()
    app.dependency_overrides[get_current_user] = mock_auth
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), Session


def test_admin_can_list_incoherent_requirements():
    c, Session = make_client(role="admin")
    db = Session()
    try:
        _seed_record(db, "r1", codes=["non_software_request"])
        _seed_record(db, "r2", codes=["conversational"])
    finally:
        db.close()

    response = c.get("/api/v1/admin/incoherent-requirements")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert len(body["items"]) == 2
    ids = {item["id"] for item in body["items"]}
    assert ids == {"r1", "r2"}


def test_member_gets_403_on_admin_endpoint():
    c, Session = make_client(role="member")
    db = Session()
    try:
        _seed_record(db, "r1")
    finally:
        db.close()
    response = c.get("/api/v1/admin/incoherent-requirements")
    assert response.status_code == 403


def test_pagination_works():
    c, Session = make_client(role="admin")
    db = Session()
    try:
        for i in range(5):
            _seed_record(db, f"r{i}")
    finally:
        db.close()

    response = c.get("/api/v1/admin/incoherent-requirements?limit=2&offset=0")
    assert response.status_code == 200
    assert response.json()["total"] == 5
    assert len(response.json()["items"]) == 2

    response = c.get("/api/v1/admin/incoherent-requirements?limit=2&offset=4")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


def test_filter_by_reason_code_works():
    c, Session = make_client(role="admin")
    db = Session()
    try:
        _seed_record(db, "r1", codes=["non_software_request"])
        _seed_record(db, "r2", codes=["conversational", "empty_intent"])
        _seed_record(db, "r3", codes=["unintelligible"])
    finally:
        db.close()

    response = c.get("/api/v1/admin/incoherent-requirements?reason=conversational")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == "r2"


def test_invalid_reason_returns_400():
    c, _Session = make_client(role="admin")
    response = c.get("/api/v1/admin/incoherent-requirements?reason=bogus")
    assert response.status_code == 400


def test_super_admin_sees_all_tenants():
    """Admin is a super-admin and sees records from all tenants."""
    c, Session = make_client(role="admin")
    db = Session()
    try:
        _seed_record(db, "mine", tenant_id=TEST_TENANT_ID)
        _seed_record(db, "other", tenant_id="other-tenant-xxxx")
    finally:
        db.close()

    response = c.get("/api/v1/admin/incoherent-requirements")
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert ids == {"mine", "other"}
    assert response.json()["total"] == 2


def test_user_email_is_resolved_when_user_exists():
    c, Session = make_client(role="admin")
    db = Session()
    try:
        # Inserta un User en el mismo tenant
        db.add(
            User(
                id=TEST_USER_ID,
                auth0_user_id="auth0|user-x",
                tenant_id=TEST_TENANT_ID,
                email="user@example.com",
                name="X",
                role="member",
                created_at=datetime.utcnow(),
            )
        )
        db.commit()
        _seed_record(db, "r1")
    finally:
        db.close()

    response = c.get("/api/v1/admin/incoherent-requirements")
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["user_email"] == "user@example.com"
