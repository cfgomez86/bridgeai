import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import create_app
from app.database.session import Base
from app.api.routes.impact_analysis import get_impact_service
from app.repositories.code_file_repository import CodeFileRepository
from app.repositories.impact_analysis_repository import ImpactAnalysisRepository
from app.services.dependency_analyzer import DependencyAnalyzer
from app.services.impact_analysis_service import ImpactAnalysisService
from app.api.routes.indexing import get_indexing_service
from app.services.code_indexing_service import CodeIndexingService


def make_client(project_root: str) -> TestClient:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    def override() -> ImpactAnalysisService:
        db = Session()
        return ImpactAnalysisService(
            CodeFileRepository(db),
            ImpactAnalysisRepository(db),
            project_root,
            DependencyAnalyzer(),
        )

    app = create_app()
    app.dependency_overrides[get_impact_service] = override
    return TestClient(app)


def make_client_with_indexing(project_root: str) -> TestClient:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    def override_impact() -> ImpactAnalysisService:
        db = Session()
        return ImpactAnalysisService(
            CodeFileRepository(db),
            ImpactAnalysisRepository(db),
            project_root,
            DependencyAnalyzer(),
        )

    def override_index() -> CodeIndexingService:
        db = Session()
        return CodeIndexingService(CodeFileRepository(db), project_root)

    app = create_app()
    app.dependency_overrides[get_impact_service] = override_impact
    app.dependency_overrides[get_indexing_service] = override_index
    return TestClient(app)


def test_post_impact_analysis_returns_200(tmp_path):
    client = make_client(str(tmp_path))
    response = client.post(
        "/api/v1/impact-analysis",
        json={"requirement": "add user email validation", "project_id": "test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "analysis_id" in data
    assert "risk_level" in data


def test_response_has_valid_uuid(tmp_path):
    client = make_client(str(tmp_path))
    response = client.post(
        "/api/v1/impact-analysis",
        json={"requirement": "add user email validation", "project_id": "test"},
    )
    assert response.status_code == 200
    data = response.json()
    uuid.UUID(data["request_id"])
    uuid.UUID(data["analysis_id"])


def test_empty_requirement_returns_400(tmp_path):
    client = make_client(str(tmp_path))
    response = client.post(
        "/api/v1/impact-analysis",
        json={"requirement": "", "project_id": "test"},
    )
    assert response.status_code == 400


def test_files_impacted_with_real_file(tmp_path):
    (tmp_path / "user_auth.py").write_text(
        "class UserAuth:\n    def validate_email(self): pass\n"
    )
    client = make_client_with_indexing(str(tmp_path))

    index_response = client.post("/api/v1/index", json={"force": False})
    assert index_response.status_code == 200

    response = client.post(
        "/api/v1/impact-analysis",
        json={"requirement": "add user email validation", "project_id": "test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["files_impacted"] >= 1


def test_risk_level_is_valid_value(tmp_path):
    client = make_client(str(tmp_path))
    response = client.post(
        "/api/v1/impact-analysis",
        json={"requirement": "add user email validation", "project_id": "test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] in ("LOW", "MEDIUM", "HIGH")
