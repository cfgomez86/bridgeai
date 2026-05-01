"""add_incoherent_requirements_table

Creates the incoherent_requirements table that stores requirements rejected
by the coherence pre-filter (LLM gate that runs before the main parser).
Each row tracks which user/tenant triggered the rejection, the original
text, the warning shown back, the reason codes, and the model that judged it.

Revision ID: e8b5f3a2c917
Revises: d4f9a1c5e802
Create Date: 2026-05-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8b5f3a2c917"
down_revision: Union[str, Sequence[str], None] = "d4f9a1c5e802"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "incoherent_requirements",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(length=36),
            sa.ForeignKey("tenants.id"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("requirement_text", sa.Text(), nullable=False),
        sa.Column("requirement_text_hash", sa.String(length=64), nullable=False),
        sa.Column("warning", sa.Text(), nullable=True),
        sa.Column("reason_codes", sa.Text(), nullable=False),
        sa.Column("project_id", sa.String(length=255), nullable=True),
        sa.Column("source_connection_id", sa.String(length=36), nullable=True),
        sa.Column("model_used", sa.String(length=120), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_incoherent_requirements_tenant_id",
        "incoherent_requirements",
        ["tenant_id"],
    )
    op.create_index(
        "ix_incoherent_requirements_user_id",
        "incoherent_requirements",
        ["user_id"],
    )
    op.create_index(
        "ix_incoherent_requirements_requirement_text_hash",
        "incoherent_requirements",
        ["requirement_text_hash"],
    )
    op.create_index(
        "ix_incoherent_requirements_tenant_created",
        "incoherent_requirements",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_incoherent_requirements_tenant_created",
        table_name="incoherent_requirements",
    )
    op.drop_index(
        "ix_incoherent_requirements_requirement_text_hash",
        table_name="incoherent_requirements",
    )
    op.drop_index(
        "ix_incoherent_requirements_user_id",
        table_name="incoherent_requirements",
    )
    op.drop_index(
        "ix_incoherent_requirements_tenant_id",
        table_name="incoherent_requirements",
    )
    op.drop_table("incoherent_requirements")
