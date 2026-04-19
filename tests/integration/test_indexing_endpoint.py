import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.indexing import get_indexing_service
from app.database.session import Base
from app.main import create_app
from app.repositories.code_file_repository import CodeFileRepository
from app.repositories.source_connection_repository import SourceConnectionRepository
from app.services.code_indexing_service import CodeIndexingService


def make_client(project_root: str) -> TestClient:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    def override() -> CodeIndexingService:
        db = Session()
        repo = CodeFileRepository(db)
        return CodeIndexingService(repo, project_root)

    app = create_app()
    app.dependency_overrides[get_indexing_service] = override
    return TestClient(app)


def test_post_index_returns_200_with_metrics(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')\n")
    client = make_client(str(tmp_path))

    response = client.post("/api/v1/index", json={"force": False})
    data = response.json()

    assert response.status_code == 200
    assert data["files_scanned"] >= 0
    assert data["duration_seconds"] >= 0


def test_post_index_with_force_returns_200(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("x = 1\n")
    client = make_client(str(tmp_path))

    response = client.post("/api/v1/index", json={"force": True})
    data = response.json()

    assert response.status_code == 200
    assert "files_scanned" in data
    assert "files_updated" in data


def test_post_index_invalid_project_root_returns_500(tmp_path: Path) -> None:
    client = make_client("/nonexistent/path/does_not_exist_xyz")

    # Mock SourceConnectionRepository to return no active connection (forces local indexing)
    with patch.object(SourceConnectionRepository, "get_active", return_value=None):
        response = client.post("/api/v1/index", json={"force": False})
        data = response.json()

    assert response.status_code == 500
    assert "detail" in data
    assert "Indexing failed" in data["detail"]


def test_response_contains_valid_uuid(tmp_path: Path) -> None:
    (tmp_path / "utils.py").write_text("pass\n")
    client = make_client(str(tmp_path))

    response = client.post("/api/v1/index", json={"force": False})
    data = response.json()

    assert response.status_code == 200
    uuid.UUID(data["request_id"])


def test_files_indexed_with_real_py_file(tmp_path: Path) -> None:
    (tmp_path / "service.py").write_text("class MyService:\n    pass\n")
    client = make_client(str(tmp_path))

    response = client.post("/api/v1/index", json={"force": False})
    data = response.json()

    assert response.status_code == 200
    assert data["files_indexed"] >= 1
