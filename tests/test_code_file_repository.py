from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.session import Base
from app.models.code_file import CodeFile
from app.repositories.code_file_repository import CodeFileRepository


@pytest.fixture
def db() -> Session:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _make_code_file(**kwargs: object) -> CodeFile:
    defaults: dict[str, object] = dict(
        file_path="/project/app/main.py",
        file_name="main.py",
        extension=".py",
        language="Python",
        size=1024,
        last_modified=datetime(2026, 1, 1, 12, 0, 0),
        hash="a" * 64,
        lines_of_code=100,
        indexed_at=datetime(2026, 1, 2, 12, 0, 0),
    )
    defaults.update(kwargs)
    return CodeFile(**defaults)


def test_save_inserts_new_record(db: Session) -> None:
    repo = CodeFileRepository(db)
    cf = _make_code_file()
    saved = repo.save(cf)
    assert saved.id is not None
    assert saved.file_path == "/project/app/main.py"
    assert saved.file_name == "main.py"


def test_find_by_path_returns_existing_record(db: Session) -> None:
    repo = CodeFileRepository(db)
    repo.save(_make_code_file())
    result = repo.find_by_path("/project/app/main.py")
    assert result is not None
    assert result.file_name == "main.py"
    assert result.extension == ".py"


def test_find_by_path_returns_none_for_missing_path(db: Session) -> None:
    repo = CodeFileRepository(db)
    result = repo.find_by_path("/nonexistent/path.py")
    assert result is None


def test_update_modifies_existing_record(db: Session) -> None:
    repo = CodeFileRepository(db)
    saved = repo.save(_make_code_file())
    saved.hash = "b" * 64
    updated = repo.update(saved)
    refetched = repo.find_by_path("/project/app/main.py")
    assert updated.hash == "b" * 64
    assert refetched is not None
    assert refetched.hash == "b" * 64


def test_list_all_returns_all_inserted_records(db: Session) -> None:
    repo = CodeFileRepository(db)
    repo.save(_make_code_file(file_path="/project/app/main.py"))
    repo.save(_make_code_file(file_path="/project/app/utils.py", file_name="utils.py"))
    repo.save(_make_code_file(file_path="/project/tests/test_main.py", file_name="test_main.py"))
    results = repo.list_all()
    paths = [r.file_path for r in results]
    assert len(results) == 3
    assert "/project/app/main.py" in paths
    assert "/project/app/utils.py" in paths
    assert "/project/tests/test_main.py" in paths
