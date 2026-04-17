from unittest.mock import MagicMock
import pytest
from pathlib import Path
from app.repositories.code_file_repository import CodeFileRepository
from app.repositories.impact_analysis_repository import ImpactAnalysisRepository
from app.services.impact_analysis_service import ImpactAnalysisService
from app.models.code_file import CodeFile
from datetime import datetime


@pytest.fixture
def repos():
    return MagicMock(spec=CodeFileRepository), MagicMock(spec=ImpactAnalysisRepository)


def make_service(code_repo, impact_repo, project_root: str) -> ImpactAnalysisService:
    return ImpactAnalysisService(code_repo, impact_repo, project_root)


def make_code_file(file_path: str, language: str = "Python") -> MagicMock:
    cf = MagicMock(spec=CodeFile)
    cf.file_path = file_path
    cf.language = language
    return cf


def test_simple_requirement_matches_file(tmp_path, repos):
    code_repo, impact_repo = repos

    (tmp_path / "user_service.py").write_text(
        "class UserService:\n    def validate_email(self): pass\n"
    )

    code_repo.iter_all.return_value = [make_code_file("user_service.py")]
    impact_repo.save.return_value = MagicMock()

    service = make_service(code_repo, impact_repo, str(tmp_path))
    result = service.analyze("Agregar validación de email en el registro de usuario", "user-service")

    assert result.files_impacted >= 1
    assert result.risk_level == "LOW"


def test_direct_dependency_is_detected(tmp_path, repos):
    code_repo, impact_repo = repos

    (tmp_path / "validator.py").write_text("class EmailValidator:\n    pass\n")
    (tmp_path / "registration.py").write_text(
        "from validator import EmailValidator\nclass Registration:\n    pass\n"
    )

    code_repo.iter_all.return_value = [
        make_code_file("validator.py"),
        make_code_file("registration.py"),
    ]
    impact_repo.save.return_value = MagicMock()

    service = make_service(code_repo, impact_repo, str(tmp_path))
    result = service.analyze("email validation", "test")

    assert result.files_impacted >= 1


def test_indirect_dependency_propagates(tmp_path, repos):
    code_repo, impact_repo = repos

    (tmp_path / "validator.py").write_text("class EmailValidator:\n    pass\n")
    (tmp_path / "registration.py").write_text(
        "import validator\nclass Registration: pass\n"
    )
    (tmp_path / "unrelated.py").write_text(
        "import registration\nclass Unrelated: pass\n"
    )

    code_repo.iter_all.return_value = [
        make_code_file("validator.py"),
        make_code_file("registration.py"),
        make_code_file("unrelated.py"),
    ]
    impact_repo.save.return_value = MagicMock()

    service = make_service(code_repo, impact_repo, str(tmp_path))
    result = service.analyze("email", "test")

    assert result.files_impacted >= 2


def test_risk_calculation(tmp_path, repos):
    code_repo, impact_repo = repos

    file_mocks = []
    for i in range(12):
        fname = f"file_{i}.py"
        (tmp_path / fname).write_text(f"# user module {i}\nclass Module{i}:\n    pass\n")
        file_mocks.append(make_code_file(fname))

    code_repo.iter_all.return_value = file_mocks
    impact_repo.save.return_value = MagicMock()

    service = make_service(code_repo, impact_repo, str(tmp_path))
    result = service.analyze("user authentication management", "test")

    assert result.risk_level == "HIGH"


def test_empty_requirement_raises_value_error(tmp_path, repos):
    code_repo, impact_repo = repos

    code_repo.iter_all.return_value = []

    service = make_service(code_repo, impact_repo, str(tmp_path))

    with pytest.raises(ValueError):
        service.analyze("  ", "proj")
