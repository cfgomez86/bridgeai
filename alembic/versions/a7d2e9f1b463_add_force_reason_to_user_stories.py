"""add force_reason to user_stories

Revision ID: a7d2e9f1b463
Revises: e8b5f3a2c917
Create Date: 2026-05-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = 'a7d2e9f1b463'
down_revision: Union[str, Sequence[str], None] = 'e8b5f3a2c917'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("user_stories")}
    if "force_reason" not in cols:
        op.add_column(
            "user_stories",
            sa.Column("force_reason", sa.String(length=20), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("user_stories")}
    if "force_reason" in cols:
        op.drop_column("user_stories", "force_reason")
