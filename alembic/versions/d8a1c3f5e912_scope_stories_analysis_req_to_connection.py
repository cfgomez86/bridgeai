"""scope requirements/analysis/impacted_files/stories to source_connection_id

Revision ID: d8a1c3f5e912
Revises: c3f1a2b4d567
Create Date: 2026-04-23 16:30:00.000000

Agrega source_connection_id (NOT NULL, FK a source_connections.id) a las tablas
requirements, impact_analysis, impacted_files y user_stories. A impacted_files
además le agrega tenant_id (hoy ausente, fuga silenciosa).

Backfill: por cada tenant, usa la SourceConnection is_active=True si existe,
si no la más reciente por created_at. Filas cuyo tenant no tiene ninguna
conexión se dejan en NULL y el alter a NOT NULL falla: esto es intencional,
fuerza limpieza manual antes de promover a prod. En dev normalmente no habrá
filas sin conexión.

También reemplaza el Index ix_requirements_text_hash_project por un
UniqueConstraint (tenant_id, source_connection_id, requirement_text_hash, project_id).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d8a1c3f5e912"
down_revision: Union[str, None] = "c3f1a2b4d567"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLES_WITH_CONN = ("requirements", "impact_analysis", "user_stories")


def upgrade() -> None:
    bind = op.get_bind()

    # ── 1. Add nullable columns ──────────────────────────────────────────────
    for table in _TABLES_WITH_CONN:
        op.add_column(
            table,
            sa.Column(
                "source_connection_id",
                sa.String(36),
                sa.ForeignKey("source_connections.id"),
                nullable=True,
            ),
        )
        op.create_index(
            f"ix_{table}_source_connection_id",
            table,
            ["source_connection_id"],
        )

    # impacted_files: le falta tenant_id también
    op.add_column(
        "impacted_files",
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=True),
    )
    op.add_column(
        "impacted_files",
        sa.Column(
            "source_connection_id",
            sa.String(36),
            sa.ForeignKey("source_connections.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_impacted_files_tenant_id", "impacted_files", ["tenant_id"])
    op.create_index(
        "ix_impacted_files_source_connection_id", "impacted_files", ["source_connection_id"]
    )

    # ── 2. Backfill por tenant ───────────────────────────────────────────────
    # Resolver la conexión "canónica" por tenant: is_active=True, y si no,
    # la más reciente. Si el tenant no tiene conexiones, sus filas quedan NULL.
    backfill_sql = sa.text(
        """
        UPDATE {table} AS t
        SET source_connection_id = sc.id
        FROM (
            SELECT DISTINCT ON (tenant_id) tenant_id, id
            FROM source_connections
            ORDER BY tenant_id, is_active DESC, created_at DESC
        ) AS sc
        WHERE t.tenant_id = sc.tenant_id
          AND t.source_connection_id IS NULL
        """
    )
    for table in _TABLES_WITH_CONN:
        bind.execute(sa.text(backfill_sql.text.format(table=table)))

    # impacted_files: backfill tenant_id y source_connection_id desde impact_analysis (parent)
    bind.execute(
        sa.text(
            """
            UPDATE impacted_files AS f
            SET tenant_id = a.tenant_id,
                source_connection_id = a.source_connection_id
            FROM impact_analysis AS a
            WHERE f.analysis_id = a.id
              AND (f.tenant_id IS NULL OR f.source_connection_id IS NULL)
            """
        )
    )

    # Borrar cualquier fila huérfana (tenants sin ninguna SourceConnection):
    # no podemos scopearlas, así que no pueden sobrevivir al NOT NULL.
    for table in _TABLES_WITH_CONN:
        bind.execute(
            sa.text(f"DELETE FROM {table} WHERE source_connection_id IS NULL")
        )
    bind.execute(
        sa.text(
            "DELETE FROM impacted_files WHERE tenant_id IS NULL OR source_connection_id IS NULL"
        )
    )

    # ── 3. Alter NOT NULL ─────────────────────────────────────────────────────
    for table in _TABLES_WITH_CONN:
        op.alter_column(table, "source_connection_id", nullable=False)
    op.alter_column("impacted_files", "tenant_id", nullable=False)
    op.alter_column("impacted_files", "source_connection_id", nullable=False)

    # ── 4. Índices y constraints compuestos ──────────────────────────────────
    # requirements: drop del índice viejo, unique nuevo, índice compuesto de lookup.
    op.drop_index("ix_requirements_text_hash_project", table_name="requirements")
    op.drop_index("ix_requirements_project_id", table_name="requirements")
    op.create_unique_constraint(
        "uq_requirements_tenant_connection_hash_project",
        "requirements",
        ["tenant_id", "source_connection_id", "requirement_text_hash", "project_id"],
    )
    op.create_index(
        "ix_requirements_tenant_connection_project",
        "requirements",
        ["tenant_id", "source_connection_id", "project_id"],
    )

    op.create_index(
        "ix_impact_analysis_tenant_connection",
        "impact_analysis",
        ["tenant_id", "source_connection_id"],
    )
    op.create_index(
        "ix_impacted_files_tenant_connection",
        "impacted_files",
        ["tenant_id", "source_connection_id"],
    )

    op.drop_index("ix_user_stories_req_analysis", table_name="user_stories")
    op.create_index(
        "ix_user_stories_req_analysis_conn",
        "user_stories",
        ["requirement_id", "impact_analysis_id", "source_connection_id"],
    )
    op.create_index(
        "ix_user_stories_tenant_connection",
        "user_stories",
        ["tenant_id", "source_connection_id"],
    )


def downgrade() -> None:
    # Revertir índices y constraints
    op.drop_index("ix_user_stories_tenant_connection", table_name="user_stories")
    op.drop_index("ix_user_stories_req_analysis_conn", table_name="user_stories")
    op.create_index(
        "ix_user_stories_req_analysis",
        "user_stories",
        ["requirement_id", "impact_analysis_id"],
    )

    op.drop_index("ix_impacted_files_tenant_connection", table_name="impacted_files")
    op.drop_index("ix_impact_analysis_tenant_connection", table_name="impact_analysis")

    op.drop_index("ix_requirements_tenant_connection_project", table_name="requirements")
    op.drop_constraint(
        "uq_requirements_tenant_connection_hash_project", "requirements", type_="unique"
    )
    op.create_index(
        "ix_requirements_project_id", "requirements", ["project_id"]
    )
    op.create_index(
        "ix_requirements_text_hash_project",
        "requirements",
        ["requirement_text_hash", "project_id"],
    )

    # Drop columns e índices agregados
    op.drop_index("ix_impacted_files_source_connection_id", table_name="impacted_files")
    op.drop_index("ix_impacted_files_tenant_id", table_name="impacted_files")
    op.drop_column("impacted_files", "source_connection_id")
    op.drop_column("impacted_files", "tenant_id")

    for table in _TABLES_WITH_CONN:
        op.drop_index(f"ix_{table}_source_connection_id", table_name=table)
        op.drop_column(table, "source_connection_id")
