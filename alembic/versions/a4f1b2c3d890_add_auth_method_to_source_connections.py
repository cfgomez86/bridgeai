"""add_auth_method_to_source_connections

Revision ID: a4f1b2c3d890
Revises: 9e9759024c61
Create Date: 2026-04-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a4f1b2c3d890'
down_revision: Union[str, Sequence[str], None] = '9e9759024c61'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'source_connections',
        sa.Column('auth_method', sa.String(10), nullable=False, server_default='oauth'),
    )


def downgrade() -> None:
    op.drop_column('source_connections', 'auth_method')
