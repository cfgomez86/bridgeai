"""add_source_connection_id_to_code_files

Revision ID: c3f1a2b4d567
Revises: b7e4f3a2c910
Create Date: 2026-04-23 15:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3f1a2b4d567"
down_revision: Union[str, None] = "b7e4f3a2c910"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the new nullable column
    op.add_column(
        "code_files",
        sa.Column(
            "source_connection_id",
            sa.String(36),
            sa.ForeignKey("source_connections.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_code_files_source_connection_id",
        "code_files",
        ["source_connection_id"],
    )

    # Replace the old unique constraint with the new three-column one
    op.drop_constraint("uq_code_files_tenant_path", "code_files", type_="unique")
    op.create_unique_constraint(
        "uq_code_files_tenant_connection_path",
        "code_files",
        ["tenant_id", "source_connection_id", "file_path"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_code_files_tenant_connection_path", "code_files", type_="unique")
    op.create_unique_constraint(
        "uq_code_files_tenant_path", "code_files", ["tenant_id", "file_path"]
    )
    op.drop_index("ix_code_files_source_connection_id", table_name="code_files")
    op.drop_column("code_files", "source_connection_id")
