"""add was_forced to user_stories

Revision ID: c1f4a8e2b73d
Revises: b2c3d4e5f6a7
Create Date: 2026-05-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = 'c1f4a8e2b73d'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("user_stories")}
    if "was_forced" not in cols:
        op.add_column(
            "user_stories",
            sa.Column(
                "was_forced",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("user_stories")}
    if "was_forced" in cols:
        op.drop_column("user_stories", "was_forced")
