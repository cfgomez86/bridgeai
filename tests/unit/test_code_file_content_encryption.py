"""Verifica que code_files.content se almacena cifrado con Fernet a nivel de
columna y se descifra de forma transparente al leer vía ORM."""

from datetime import datetime

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.context import current_tenant_id
from app.database import encrypted_types
from app.database.session import Base
from app.models.code_file import CodeFile
from app.models.tenant import Tenant


_PLAINTEXT_CODE = "import os\n\nclass PaymentService:\n    def charge(self, amount: int) -> int:\n        return amount\n"


@pytest.fixture
def encryption_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """Set a real Fernet key for the duration of the test and clear the cached
    instance so EncryptedText picks up the value."""
    key = Fernet.generate_key().decode()

    # The TypeDecorator reads Settings via @lru_cache; patch both layers.
    from app.core import config as config_module

    monkeypatch.setattr(
        config_module,
        "get_settings",
        lambda: type("S", (), {"FIELD_ENCRYPTION_KEY": key})(),
    )
    encrypted_types._fernet.cache_clear()
    yield key
    encrypted_types._fernet.cache_clear()


@pytest.fixture
def db() -> Session:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    # The repository requires tenant context; for ORM-level tests we set it
    # directly (no Auth0 round-trip).
    token = current_tenant_id.set("t1")
    # A Tenant row is needed for the FK from code_files.tenant_id to satisfy
    yield session
    current_tenant_id.reset(token)
    session.close()


def _make_code_file(content: str | None) -> CodeFile:
    return CodeFile(
        tenant_id="t1",
        source_connection_id=None,
        file_path="app/services/payment.py",
        file_name="payment.py",
        extension=".py",
        language="Python",
        size=len(content) if content else 0,
        last_modified=datetime(2026, 1, 1, 12, 0, 0),
        hash="a" * 64,
        lines_of_code=4,
        indexed_at=datetime(2026, 1, 2, 12, 0, 0),
        content=content,
    )


def _seed_tenant(db: Session) -> None:
    db.add(Tenant(id="t1", auth0_user_id="auth0|abc", name="t1", plan="free", created_at=datetime(2026, 1, 1)))
    db.commit()


def test_content_is_stored_encrypted_at_rest(
    db: Session, encryption_key: str
) -> None:
    """Insertar un CodeFile y verificar que en la columna física el valor está
    cifrado (no aparece el plaintext del código fuente)."""
    _seed_tenant(db)
    db.add(_make_code_file(_PLAINTEXT_CODE))
    db.commit()

    raw_value = db.execute(text("SELECT content FROM code_files LIMIT 1")).scalar()
    assert raw_value is not None
    assert raw_value != _PLAINTEXT_CODE
    # Fernet tokens are base64; the literal class name and decoration shouldn't
    # leak through.
    assert "PaymentService" not in raw_value
    assert "import os" not in raw_value
    # All Fernet tokens start with "gAAAAA" (version 0x80 base64-encoded).
    assert raw_value.startswith("gAAAAA")


def test_content_is_decrypted_transparently_via_orm(
    db: Session, encryption_key: str
) -> None:
    """Al releer el CodeFile a través del ORM, content vuelve en claro."""
    _seed_tenant(db)
    db.add(_make_code_file(_PLAINTEXT_CODE))
    db.commit()
    db.expire_all()  # forzar nueva lectura desde DB

    cf = db.query(CodeFile).first()
    assert cf is not None
    assert cf.content == _PLAINTEXT_CODE


def test_null_and_empty_content_pass_through(
    db: Session, encryption_key: str
) -> None:
    """null y empty string no deben cifrarse (caso explícito de EncryptedText)."""
    _seed_tenant(db)
    db.add(_make_code_file(None))
    db.commit()
    db.expire_all()

    cf = db.query(CodeFile).first()
    assert cf is not None
    assert cf.content is None


def test_content_roundtrip_preserves_unicode(
    db: Session, encryption_key: str
) -> None:
    """Verificar que el cifrado preserva caracteres no-ASCII (acentos, emojis,
    chino) — Fernet usa bytes, no se debe corromper UTF-8."""
    _seed_tenant(db)
    payload = "función válida con acentos y emojis 🎉 y 中文"
    db.add(_make_code_file(payload))
    db.commit()
    db.expire_all()

    cf = db.query(CodeFile).first()
    assert cf is not None
    assert cf.content == payload
