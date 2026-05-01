"""encrypt_code_file_content

Data migration that encrypts existing plaintext values of code_files.content
using Fernet symmetric encryption. Mirrors the pattern of
b5e2c3d4f901_encrypt_token_fields.

Requires FIELD_ENCRYPTION_KEY to be set in the environment before running.
If not set, migration is skipped with a warning — run again after setting the key.

Generate a key:
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Revision ID: d4f9a1c5e802
Revises: c1f4a8e2b73d
Create Date: 2026-05-01 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4f9a1c5e802"
down_revision: Union[str, Sequence[str], None] = "c1f4a8e2b73d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_BATCH_SIZE = 500


def upgrade() -> None:
    import os

    key = os.environ.get("FIELD_ENCRYPTION_KEY", "")
    if not key:
        print(
            "\nWARNING: FIELD_ENCRYPTION_KEY not set — code_files.content encryption skipped.\n"
            "Set the key and run 'python -m alembic upgrade head' again to encrypt existing content.\n"
        )
        return

    from cryptography.fernet import Fernet, InvalidToken

    f = Fernet(key.encode() if isinstance(key, str) else key)
    bind = op.get_bind()

    total_rows = bind.execute(
        sa.text("SELECT COUNT(*) FROM code_files WHERE content IS NOT NULL AND content != ''")
    ).scalar() or 0
    if total_rows == 0:
        print("\nNo code_files.content rows to encrypt.\n")
        return

    print(f"\nEncrypting {total_rows} code_files.content row(s) in batches of {_BATCH_SIZE}...")

    encrypted_count = 0
    skipped_count = 0
    last_id = 0

    while True:
        rows = bind.execute(
            sa.text(
                "SELECT id, content FROM code_files "
                "WHERE id > :last_id AND content IS NOT NULL AND content != '' "
                "ORDER BY id ASC LIMIT :limit"
            ),
            {"last_id": last_id, "limit": _BATCH_SIZE},
        ).fetchall()
        if not rows:
            break

        for row in rows:
            last_id = row.id
            try:
                f.decrypt(row.content.encode())
                skipped_count += 1
                continue
            except (InvalidToken, Exception):
                pass

            enc = f.encrypt(row.content.encode()).decode()
            bind.execute(
                sa.text("UPDATE code_files SET content = :c WHERE id = :id"),
                {"c": enc, "id": row.id},
            )
            encrypted_count += 1

    print(
        f"Done. Encrypted {encrypted_count} row(s); "
        f"{skipped_count} already encrypted (idempotent re-run).\n"
    )


def downgrade() -> None:
    import os

    key = os.environ.get("FIELD_ENCRYPTION_KEY", "")
    if not key:
        print(
            "\nWARNING: FIELD_ENCRYPTION_KEY not set — cannot decrypt code_files.content on downgrade. Skipping.\n"
        )
        return

    from cryptography.fernet import Fernet, InvalidToken

    f = Fernet(key.encode() if isinstance(key, str) else key)
    bind = op.get_bind()
    last_id = 0

    while True:
        rows = bind.execute(
            sa.text(
                "SELECT id, content FROM code_files "
                "WHERE id > :last_id AND content IS NOT NULL AND content != '' "
                "ORDER BY id ASC LIMIT :limit"
            ),
            {"last_id": last_id, "limit": _BATCH_SIZE},
        ).fetchall()
        if not rows:
            break

        for row in rows:
            last_id = row.id
            try:
                plain = f.decrypt(row.content.encode()).decode()
            except InvalidToken:
                continue  # already plaintext
            bind.execute(
                sa.text("UPDATE code_files SET content = :c WHERE id = :id"),
                {"c": plain, "id": row.id},
            )
