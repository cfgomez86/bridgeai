"""Cifra in-place las filas de code_files.content que aún están en plaintext.

Cuándo usarlo
-------------
Cuando la migración d4f9a1c5e802_encrypt_code_file_content corrió ANTES de que
FIELD_ENCRYPTION_KEY estuviera configurada. En ese caso la migración quedó
marcada como aplicada pero no transformó datos existentes; los rows nuevos
sí se cifran al insertar (lo hace EncryptedText en runtime), pero los viejos
permanecen en claro hasta que pase este script.

Es idempotente: cada fila se intenta descifrar primero; si descifra OK, ya
estaba cifrada y se salta. Re-correrlo no causa daño.

Uso local
---------
    python scripts/encrypt_existing_content.py

Uso en Railway
--------------
    railway run python scripts/encrypt_existing_content.py

(Railway carga las variables de entorno del proyecto, incluyendo
FIELD_ENCRYPTION_KEY. La conexión a Postgres se resuelve via DATABASE_URL.)

Salida
------
Reporta cuántas filas cifró, cuántas ya estaban cifradas y cuántas
no pudieron procesarse (con error para diagnóstico).
"""
from __future__ import annotations

import sys

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import text

from app.core.config import get_settings
from app.database.session import engine

_BATCH_SIZE = 500


def main() -> int:
    settings = get_settings()
    key = settings.FIELD_ENCRYPTION_KEY
    if not key:
        print(
            "FIELD_ENCRYPTION_KEY no configurada. Define la clave en .env "
            "(o en las variables de Railway) y vuelve a ejecutar.",
            file=sys.stderr,
        )
        return 2

    fernet = Fernet(key.encode() if isinstance(key, str) else key)

    with engine.begin() as conn:
        total = conn.execute(
            text(
                "SELECT COUNT(*) FROM code_files "
                "WHERE content IS NOT NULL AND content != ''"
            )
        ).scalar() or 0

        if total == 0:
            print("No hay filas con content en code_files. Nada que cifrar.")
            return 0

        print(
            f"Encontradas {total} filas con content. "
            f"Procesando en batches de {_BATCH_SIZE}..."
        )

        encrypted = 0
        already_encrypted = 0
        errors = 0
        last_id = 0

        while True:
            rows = conn.execute(
                text(
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

                # Idempotencia: si descifra correctamente, ya está cifrada.
                try:
                    fernet.decrypt(row.content.encode())
                    already_encrypted += 1
                    continue
                except InvalidToken:
                    pass
                except Exception as exc:
                    errors += 1
                    print(f"  WARN id={row.id}: error al inspeccionar: {exc}")
                    continue

                try:
                    enc = fernet.encrypt(row.content.encode()).decode()
                except Exception as exc:
                    errors += 1
                    print(f"  WARN id={row.id}: error al cifrar: {exc}")
                    continue

                conn.execute(
                    text("UPDATE code_files SET content = :c WHERE id = :id"),
                    {"c": enc, "id": row.id},
                )
                encrypted += 1

        print(
            f"Listo: {encrypted} cifrada(s), "
            f"{already_encrypted} ya estaban cifradas, "
            f"{errors} con errores."
        )
        return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
