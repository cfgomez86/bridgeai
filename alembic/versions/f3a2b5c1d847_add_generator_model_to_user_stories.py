"""add generator_model to user_stories

Revision ID: f3a2b5c1d847
Revises: e7b1c4a3d925
Create Date: 2026-04-30 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = 'f3a2b5c1d847'
down_revision: Union[str, Sequence[str], None] = 'e7b1c4a3d925'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("user_stories")}
    if "generator_model" not in cols:
        op.add_column(
            "user_stories",
            sa.Column("generator_model", sa.String(length=100), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("user_stories")}
    if "generator_model" in cols:
        op.drop_column("user_stories", "generator_model")
