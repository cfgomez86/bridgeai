"""encrypt_token_fields

Data migration that encrypts existing plaintext access_token and refresh_token values
in source_connections using Fernet symmetric encryption.

Requires FIELD_ENCRYPTION_KEY to be set in the environment before running.
If not set, migration is skipped with a warning — run again after setting the key.

Generate a key:
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Revision ID: b5e2c3d4f901
Revises: a4f1b2c3d890
Create Date: 2026-04-27 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b5e2c3d4f901'
down_revision: Union[str, Sequence[str], None] = 'a4f1b2c3d890'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    import os
    key = os.environ.get("FIELD_ENCRYPTION_KEY", "")
    if not key:
        print(
            "\nWARNING: FIELD_ENCRYPTION_KEY not set — token encryption skipped.\n"
            "Set the key and run 'python -m alembic upgrade head' again to encrypt existing tokens.\n"
        )
        return

    from cryptography.fernet import Fernet, InvalidToken
    f = Fernet(key.encode() if isinstance(key, str) else key)

    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, access_token, refresh_token FROM source_connections WHERE access_token != ''")
    ).fetchall()

    encrypted_count = 0
    for row in rows:
        # Skip rows that are already encrypted (idempotent re-runs)
        try:
            f.decrypt(row.access_token.encode())
            continue
        except (InvalidToken, Exception):
            pass

        enc_access = f.encrypt(row.access_token.encode()).decode()
        enc_refresh = f.encrypt(row.refresh_token.encode()).decode() if row.refresh_token else None

        bind.execute(
            sa.text(
                "UPDATE source_connections SET access_token = :a, refresh_token = :r WHERE id = :id"
            ),
            {"a": enc_access, "r": enc_refresh, "id": str(row.id)},
        )
        encrypted_count += 1

    print(f"\nEncrypted {encrypted_count} token(s) in source_connections.\n")


def downgrade() -> None:
    # Decryption on downgrade requires the key — if it's gone, data is irrecoverable.
    import os
    key = os.environ.get("FIELD_ENCRYPTION_KEY", "")
    if not key:
        print("\nWARNING: FIELD_ENCRYPTION_KEY not set — cannot decrypt tokens on downgrade. Skipping.\n")
        return

    from cryptography.fernet import Fernet, InvalidToken
    f = Fernet(key.encode() if isinstance(key, str) else key)

    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, access_token, refresh_token FROM source_connections WHERE access_token != ''")
    ).fetchall()

    for row in rows:
        try:
            plain_access = f.decrypt(row.access_token.encode()).decode()
        except InvalidToken:
            continue  # already plaintext
        plain_refresh = None
        if row.refresh_token:
            try:
                plain_refresh = f.decrypt(row.refresh_token.encode()).decode()
            except InvalidToken:
                plain_refresh = row.refresh_token

        bind.execute(
            sa.text(
                "UPDATE source_connections SET access_token = :a, refresh_token = :r WHERE id = :id"
            ),
            {"a": plain_access, "r": plain_refresh, "id": str(row.id)},
        )
