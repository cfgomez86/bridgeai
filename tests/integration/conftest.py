"""
Integration test configuration and fixtures.

Integration tests focus on endpoints and services with TestClient.
They use in-memory SQLite database and dependency injection overrides.
"""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.database.session import Base, get_db
from app.main import create_app
from tests.integration.auth_helpers import mock_auth as _mock_auth, apply_mock_auth, TEST_TENANT_ID, TEST_USER_ID


@pytest.fixture(scope="function")
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()


@pytest.fixture(scope="function")
def client() -> TestClient:
    """TestClient with real PostgreSQL and mock auth."""
    app = create_app()
    app.dependency_overrides[get_current_user] = _mock_auth
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client_with_in_memory_db(in_memory_db):
    """TestClient with in-memory SQLite and mock auth."""
    def override_get_db():
        try:
            yield in_memory_db
        finally:
            pass

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = _mock_auth

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
