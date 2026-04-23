from unittest.mock import MagicMock
import pytest

from app.repositories.code_file_repository import CodeFileRepository
from app.repositories.impact_analysis_repository import ImpactAnalysisRepository
from app.services.impact_analysis_service import ImpactAnalysisService
from app.models.code_file import CodeFile


_CONN = "conn-1"


@pytest.fixture
def repos():
    return MagicMock(spec=CodeFileRepository), MagicMock(spec=ImpactAnalysisRepository)


def make_service(code_repo, impact_repo, project_root: str) -> ImpactAnalysisService:
    return ImpactAnalysisService(code_repo, impact_repo, project_root)


def make_code_file(
    file_path: str, language: str = "Python", content: str | None = None
) -> MagicMock:
    cf = MagicMock(spec=CodeFile)
    cf.file_path = file_path
    cf.language = language
    cf.content = content
    return cf


def test_simple_requirement_matches_file(tmp_path, repos):
    code_repo, impact_repo = repos

    (tmp_path / "user_service.py").write_text(
        "class UserService:\n    def validate_email(self): pass\n"
    )

    code_repo.iter_all.return_value = [make_code_file("user_service.py")]
    impact_repo.save.return_value = MagicMock()

    service = make_service(code_repo, impact_repo, str(tmp_path))
    result = service.analyze(
        "Agregar validación de email en el registro de usuario", "user-service", _CONN
    )

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
    result = service.analyze("email validation", "test", _CONN)

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
    result = service.analyze("email", "test", _CONN)

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
    result = service.analyze("user authentication management", "test", _CONN)

    assert result.risk_level == "HIGH"


def test_empty_requirement_raises_value_error(tmp_path, repos):
    code_repo, impact_repo = repos
    code_repo.iter_all.return_value = []
    service = make_service(code_repo, impact_repo, str(tmp_path))
    with pytest.raises(ValueError):
        service.analyze("  ", "proj", _CONN)


def test_missing_connection_raises_value_error(tmp_path, repos):
    code_repo, impact_repo = repos
    service = make_service(code_repo, impact_repo, str(tmp_path))
    with pytest.raises(ValueError, match="source_connection_id"):
        service.analyze("hola", "proj", "")


def test_accented_keyword_matches_unaccented_code(tmp_path, repos):
    """Requerimiento con acentos (ES) debe matchear código que comparte la raíz sin acento."""
    code_repo, impact_repo = repos

    (tmp_path / "Notifier.java").write_text(
        "public class Notifier {\n"
        "    // Servicio de notificación por email\n"
        "    public void send() {}\n"
        "}\n"
    )
    code_repo.iter_all.return_value = [
        make_code_file("Notifier.java", language="Java")
    ]
    impact_repo.save.return_value = MagicMock()

    service = make_service(code_repo, impact_repo, str(tmp_path))
    result = service.analyze(
        "Actualizar servicio de notificación por email",
        "proj",
        _CONN,
    )
    assert result.files_impacted >= 1


def test_three_char_keyword_now_matches(tmp_path, repos):
    """Con el umbral bajado a 3, 'api' debe producir matches."""
    code_repo, impact_repo = repos
    (tmp_path / "ApiRouter.java").write_text(
        "public class ApiRouter { public void route() {} }\n"
    )
    code_repo.iter_all.return_value = [
        make_code_file("ApiRouter.java", language="Java")
    ]
    impact_repo.save.return_value = MagicMock()

    service = make_service(code_repo, impact_repo, str(tmp_path))
    result = service.analyze("Nueva api de reportes", "proj", _CONN)
    assert result.files_impacted >= 1


def test_uses_db_content_when_available(tmp_path, repos):
    """Si cf.content no es None, no debe leer del filesystem (repo remoto)."""
    code_repo, impact_repo = repos

    cf = make_code_file(
        "remote/NotificationService.java",
        language="Java",
        content="public class NotificationService { public void notify() {} }",
    )
    code_repo.iter_all.return_value = [cf]
    impact_repo.save.return_value = MagicMock()

    service = make_service(code_repo, impact_repo, str(tmp_path))
    result = service.analyze("Notification change", "proj", _CONN)
    assert result.files_impacted >= 1


def test_scopes_file_iteration_to_connection(tmp_path, repos):
    code_repo, impact_repo = repos
    code_repo.iter_all.return_value = []
    impact_repo.save.return_value = MagicMock()
    service = make_service(code_repo, impact_repo, str(tmp_path))
    service.analyze("requirement text", "proj", "conn-xyz")
    # El repo de code_files debe haber sido llamado con la conexión explícita
    code_repo.iter_all.assert_called_once()
    kwargs = code_repo.iter_all.call_args.kwargs
    assert kwargs.get("source_connection_id") == "conn-xyz"
    # Y el save del análisis también debe llevar la connection
    impact_repo.save.assert_called_once()
    save_args = impact_repo.save.call_args
    # save(analysis, impacted_files, source_connection_id)
    assert save_args.args[2] == "conn-xyz" if len(save_args.args) >= 3 else save_args.kwargs.get("source_connection_id") == "conn-xyz"
