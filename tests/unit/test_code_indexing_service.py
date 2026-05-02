"""
Tests for CodeIndexingService — language detection, ignore patterns, incremental updates, batch operations.
"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import hashlib
from datetime import datetime

from app.services.code_indexing_service import CodeIndexingService, DEFAULT_LANGUAGE_MAP, DEFAULT_IGNORE_PATTERNS
from app.core.config import Settings
from app.domain.file_info import FileInfo
from app.repositories.code_file_repository import CodeFileRepository
from app.models.code_file import CodeFile


def _sha256(file_path: Path) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


@pytest.fixture
def repo() -> MagicMock:
    return MagicMock(spec=CodeFileRepository)


def test_new_file_is_inserted(repo: MagicMock, tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')\n")
    repo.find_by_path.return_value = None

    service = CodeIndexingService(repository=repo, project_root=str(tmp_path))
    result = service.index_repository()

    assert repo.save_batch.called is True
    assert repo.update_batch.called is False
    assert result.files_indexed == 1
    assert result.files_skipped == 0


def test_modified_file_is_updated(repo: MagicMock, tmp_path: Path) -> None:
    file_path = tmp_path / "utils.py"
    file_path.write_text("x = 1\n")

    mock_cf = MagicMock(spec=CodeFile)
    mock_cf.hash = "0" * 64
    repo.find_by_path.return_value = mock_cf

    service = CodeIndexingService(repository=repo, project_root=str(tmp_path))
    result = service.index_repository()

    assert repo.update_batch.called is True
    assert repo.save_batch.called is False
    assert result.files_updated == 1


def test_unchanged_file_is_skipped(repo: MagicMock, tmp_path: Path) -> None:
    file_path = tmp_path / "config.py"
    file_path.write_text("DEBUG = True\n")
    real_hash = _sha256(file_path)

    mock_cf = MagicMock(spec=CodeFile)
    mock_cf.hash = real_hash
    repo.find_by_path.return_value = mock_cf

    service = CodeIndexingService(repository=repo, project_root=str(tmp_path))
    result = service.index_repository()

    assert repo.save_batch.called is False
    assert repo.update_batch.called is False
    assert result.files_skipped == 1


def test_ignored_directory_is_not_scanned(repo: MagicMock, tmp_path: Path) -> None:
    pycache_dir = tmp_path / "__pycache__"
    pycache_dir.mkdir()
    (pycache_dir / "module.py").write_text("# cached\n")
    (tmp_path / "main.py").write_text("# main\n")
    repo.find_by_path.return_value = None

    service = CodeIndexingService(repository=repo, project_root=str(tmp_path))
    service.index_repository()

    assert repo.save_batch.call_count == 1


def test_force_reindexes_unchanged_file(repo: MagicMock, tmp_path: Path) -> None:
    file_path = tmp_path / "app.py"
    file_path.write_text("SOME_SETTING = 42\n")
    real_hash = _sha256(file_path)

    mock_cf = MagicMock(spec=CodeFile)
    mock_cf.hash = real_hash
    repo.find_by_path.return_value = mock_cf

    service = CodeIndexingService(repository=repo, project_root=str(tmp_path))
    result = service.index_repository(force=True)

    assert repo.update_batch.called is True
    assert result.files_updated == 1
    assert result.files_skipped == 0


def test_invalid_project_root_raises_value_error(repo: MagicMock) -> None:
    service = CodeIndexingService(repository=repo, project_root="/nonexistent/path/xyz")

    with pytest.raises(ValueError):
        service.index_repository()
