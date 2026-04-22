"""drop_platform_configs

Revision ID: e1a62213dda8
Revises: 719f4fee3415
Create Date: 2026-04-22 19:10:59.924152

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e1a62213dda8'
down_revision: Union[str, Sequence[str], None] = '719f4fee3415'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('platform_configs')


def downgrade() -> None:
    op.create_table(
        'platform_configs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('client_id', sa.String(length=255), nullable=False),
        sa.Column('client_secret', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'platform', name='uq_platform_configs_tenant_platform'),
    )
    op.create_index('ix_platform_configs_tenant_id', 'platform_configs', ['tenant_id'])
