from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _build_engine():  # type: ignore[no-untyped-def]
    settings = get_settings()
    kwargs: dict = {
        "echo": False,
        "future": True,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,
    }
    return create_engine(settings.DATABASE_URL, **kwargs)


engine = _build_engine()

SessionLocal: sessionmaker[Session] = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Return True if the database is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
