import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _fernet():
    from app.core.config import get_settings
    key = get_settings().FIELD_ENCRYPTION_KEY
    if not key:
        return None
    return Fernet(key.encode() if isinstance(key, str) else key)


class EncryptedText(TypeDecorator):
    """SQLAlchemy TypeDecorator that transparently encrypts/decrypts field values.

    Requires FIELD_ENCRYPTION_KEY in settings (valid Fernet key).
    When key is absent, values pass through unencrypted with a warning — this
    allows zero-downtime rollout: set the key, then run the encrypt migration.
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None or value == "":
            return value
        f = _fernet()
        if f is None:
            logger.warning("FIELD_ENCRYPTION_KEY not set — token stored unencrypted (set key and run migrations)")
            return value
        return f.encrypt(value.encode()).decode()

    def process_result_value(self, value, dialect):
        if value is None or value == "":
            return value
        f = _fernet()
        if f is None:
            return value
        try:
            return f.decrypt(value.encode()).decode()
        except InvalidToken:
            # Pre-migration plaintext value — return as-is and warn
            logger.warning("Unencrypted token found in DB — run: python -m alembic upgrade head")
            return value
