"""add_base_url_to_source_connections

Revision ID: f3c2a1d4e089
Revises: 88c94e7fd264
Create Date: 2026-04-23 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3c2a1d4e089'
down_revision: Union[str, Sequence[str], None] = '88c94e7fd264'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('source_connections', sa.Column('base_url', sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column('source_connections', 'base_url')
