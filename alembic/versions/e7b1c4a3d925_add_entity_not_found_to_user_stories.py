"""add entity_not_found to user_stories

Revision ID: e7b1c4a3d925
Revises: d1e2f3a4b567
Create Date: 2026-04-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = 'e7b1c4a3d925'
down_revision: Union[str, Sequence[str], None] = 'd1e2f3a4b567'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("user_stories")}
    if "entity_not_found" not in cols:
        op.add_column(
            "user_stories",
            sa.Column(
                "entity_not_found",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("user_stories")}
    if "entity_not_found" in cols:
        op.drop_column("user_stories", "entity_not_found")
