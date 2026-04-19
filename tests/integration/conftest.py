"""
Integration test configuration and fixtures.

Integration tests focus on endpoints and services with TestClient.
They use in-memory SQLite database and dependency injection overrides.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.database.session import Base, get_db


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
    """Create a TestClient with a real database connection (PostgreSQL)."""
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def client_with_in_memory_db(in_memory_db):
    """Create a TestClient with in-memory database override."""
    def override_get_db():
        try:
            yield in_memory_db
        finally:
            pass

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as c:
        yield c
    
    app.dependency_overrides.clear()
