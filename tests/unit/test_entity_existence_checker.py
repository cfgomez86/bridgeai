from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base
from app.models.code_file import CodeFile
from app.repositories.code_file_repository import CodeFileRepository
from app.services.dependency_analyzer import DependencyAnalyzer
from app.services.entity_existence_checker import (
    EntityCheckResult,
    EntityExistenceChecker,
)
from tests.unit.conftest import TEST_CONNECTION_ID, TEST_TENANT_ID


def make_repo():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    return CodeFileRepository(db), db


def add_code_file(db, *, file_path: str, content: str, language: str = "Python") -> None:
    cf = CodeFile(
        tenant_id=TEST_TENANT_ID,
        source_connection_id=TEST_CONNECTION_ID,
        file_path=file_path,
        file_name=file_path.split("/")[-1],
        extension="py",
        language=language,
        size=len(content),
        last_modified=datetime.now(timezone.utc),
        hash="h" * 64,
        lines_of_code=content.count("\n") + 1,
        indexed_at=datetime.now(timezone.utc),
        content=content,
    )
    db.add(cf)
    db.commit()


def make_checker(repo: CodeFileRepository) -> EntityExistenceChecker:
    return EntityExistenceChecker(
        code_file_repo=repo,
        analyzer=DependencyAnalyzer(TEST_TENANT_ID),
    )


def test_exact_match_case_insensitive():
    repo, db = make_repo()
    add_code_file(db, file_path="app/models/product.py", content="class Product:\n    pass\n")
    checker = make_checker(repo)
    result = checker.check("Product", TEST_CONNECTION_ID)
    assert result.found is True
    assert "app/models/product.py" in result.matched_files
    assert result.suggestions == []


def test_exact_match_lowercase_entity_uppercase_class():
    repo, db = make_repo()
    add_code_file(db, file_path="m.py", content="class Product:\n    pass\n")
    checker = make_checker(repo)
    result = checker.check("product", TEST_CONNECTION_ID)
    assert result.found is True


def test_camelcase_prefix_matches_product_model():
    repo, db = make_repo()
    add_code_file(db, file_path="m.py", content="class ProductModel:\n    pass\n")
    checker = make_checker(repo)
    result = checker.check("Product", TEST_CONNECTION_ID)
    assert result.found is True


def test_camelcase_prefix_does_not_match_lowercase_continuation():
    """Product NO debe matchear Productivity (no es CamelCase boundary)."""
    repo, db = make_repo()
    add_code_file(db, file_path="m.py", content="class Productivity:\n    pass\n")
    checker = make_checker(repo)
    result = checker.check("Product", TEST_CONNECTION_ID)
    assert result.found is False


def test_cross_language_es_to_en():
    repo, db = make_repo()
    add_code_file(db, file_path="m.py", content="class Product:\n    pass\n")
    checker = make_checker(repo)
    result = checker.check("Producto", TEST_CONNECTION_ID)
    assert result.found is True


def test_cross_language_en_to_es():
    repo, db = make_repo()
    add_code_file(db, file_path="m.py", content="class Producto:\n    pass\n")
    checker = make_checker(repo)
    result = checker.check("Product", TEST_CONNECTION_ID)
    assert result.found is True


def test_skip_generic_entity():
    repo, _ = make_repo()
    # Codebase vacío — pero "system" es genérica, debe devolver found=True
    checker = make_checker(repo)
    result = checker.check("system", TEST_CONNECTION_ID)
    assert result.found is True
    assert result.matched_files == []


def test_skip_empty_entity():
    repo, _ = make_repo()
    checker = make_checker(repo)
    result = checker.check("", TEST_CONNECTION_ID)
    assert result.found is True


def test_not_found_returns_suggestions():
    repo, db = make_repo()
    add_code_file(db, file_path="a.py", content="class ProductService:\n    pass\n")
    add_code_file(db, file_path="b.py", content="class ProductRepository:\n    pass\n")
    add_code_file(db, file_path="c.py", content="class OrderService:\n    pass\n")
    checker = make_checker(repo)
    result = checker.check("ProductoInexistente", TEST_CONNECTION_ID)
    assert result.found is False
    # ProductService y ProductRepository deberían sugerirse (substring 'product')
    assert any("Product" in s for s in result.suggestions)


def test_no_suggestions_when_codebase_empty():
    repo, _db = make_repo()
    checker = make_checker(repo)
    result = checker.check("ProductoInexistente", TEST_CONNECTION_ID)
    assert result.found is False
    assert result.suggestions == []


def test_files_without_content_are_skipped():
    repo, db = make_repo()
    cf = CodeFile(
        tenant_id=TEST_TENANT_ID,
        source_connection_id=TEST_CONNECTION_ID,
        file_path="empty.py",
        file_name="empty.py",
        extension="py",
        language="Python",
        size=0,
        last_modified=datetime.now(timezone.utc),
        hash="h" * 64,
        lines_of_code=0,
        indexed_at=datetime.now(timezone.utc),
        content=None,
    )
    db.add(cf)
    db.commit()
    checker = make_checker(repo)
    result = checker.check("Product", TEST_CONNECTION_ID)
    assert result.found is False
    assert result.matched_files == []


def test_match_returns_first_file_per_class():
    repo, db = make_repo()
    add_code_file(db, file_path="a.py", content="class Product:\n    pass\n")
    add_code_file(db, file_path="b.py", content="class Product:\n    pass\n")
    checker = make_checker(repo)
    result = checker.check("Product", TEST_CONNECTION_ID)
    assert result.found is True
    assert sorted(result.matched_files) == ["a.py", "b.py"]


def test_suggestions_top_5_only():
    repo, db = make_repo()
    for i in range(10):
        add_code_file(db, file_path=f"file{i}.py", content=f"class ProductX{i}:\n    pass\n")
    checker = make_checker(repo)
    # Buscamos "ProductoInexistente" — todas las clases ProductX* sugeridas, max 5
    result = checker.check("ProductoZZZZ", TEST_CONNECTION_ID)
    assert result.found is False
    assert len(result.suggestions) <= 5


def test_underscore_variant_matches_camelcase_class():
    """user_story (snake_case from AI) debe matchear class UserStory."""
    repo, db = make_repo()
    add_code_file(db, file_path="m.py", content="class UserStory:\n    pass\n")
    checker = make_checker(repo)
    result = checker.check("user_story", TEST_CONNECTION_ID)
    assert result.found is True


def test_underscore_variant_matches_camelcase_with_suffix():
    """user_story debe matchear class UserStoryModel (CamelCase boundary tras underscore-strip)."""
    repo, db = make_repo()
    add_code_file(db, file_path="m.py", content="class UserStoryModel:\n    pass\n")
    checker = make_checker(repo)
    result = checker.check("user_story", TEST_CONNECTION_ID)
    assert result.found is True


def test_meta_app_entities_are_generic():
    """Términos meta del propio app (historia, story, requerimiento, ticket, formulario...)
    deben tratarse como genéricos para no bloquear historias válidas."""
    repo, _db = make_repo()
    checker = make_checker(repo)
    for entity in (
        "historia", "story", "user_story",
        "requerimiento", "requirement",
        "ticket", "tiquet",
        "formulario", "form",
        "pantalla", "screen",
        "página", "pagina", "page",
        "detalle", "detalles", "detail", "details",
    ):
        result = checker.check(entity, TEST_CONNECTION_ID)
        assert result.found is True, f"'{entity}' debería ser genérico"


def test_historia_maps_to_story_via_equivalences():
    """Cuando la AI extrae 'historia' y existe class Story, debe encontrarla."""
    repo, db = make_repo()
    add_code_file(db, file_path="m.py", content="class Story:\n    pass\n")
    checker = make_checker(repo)
    # historia está en _GENERIC_ENTITIES, pero también en equivalencias.
    # Si en el futuro se quita de genéricos, este test cubre el mapping.
    result = checker.check("historia", TEST_CONNECTION_ID)
    assert result.found is True
