"""add_connection_audit_log

Revision ID: c6d3e4f5a012
Revises: b5e2c3d4f901
Create Date: 2026-04-27 00:02:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c6d3e4f5a012'
down_revision: Union[str, Sequence[str], None] = 'b5e2c3d4f901'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'connection_audit_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('connection_id', sa.String(36), nullable=False, index=True),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('auth_method', sa.String(10), nullable=False),
        sa.Column('event', sa.String(50), nullable=False),
        sa.Column('actor', sa.String(255), nullable=False),
        sa.Column('detail', sa.Text, nullable=True),
        sa.Column('timestamp', sa.DateTime, nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table('connection_audit_logs')
