"""add dispersion samples_used evidence to story_quality_score

Revision ID: b9d4f7e2c815
Revises: a03dd37be40a
Create Date: 2026-04-29 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b9d4f7e2c815"
down_revision: Union[str, None] = "a03dd37be40a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("story_quality_score", sa.Column("dispersion", sa.Float(), nullable=True))
    op.add_column("story_quality_score", sa.Column("samples_used", sa.Integer(), nullable=True))
    op.add_column("story_quality_score", sa.Column("evidence", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("story_quality_score", "evidence")
    op.drop_column("story_quality_score", "samples_used")
    op.drop_column("story_quality_score", "dispersion")
