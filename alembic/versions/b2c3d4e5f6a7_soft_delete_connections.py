"""soft delete connections, restore NOT NULL on source_connection_id

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-30 19:00:00.000000

Add deleted_at to source_connections so that disconnecting a repo only
soft-deletes the connection row. Historical stories, requirements, and
analyses keep their source_connection_id intact, preserving full
traceability. The code index (code_files, impacted_files) is still
physically deleted on disconnect.

Also restores NOT NULL on source_connection_id in the three tables that
the previous migration made nullable — no NULLs were ever written, so
this is safe.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'source_connections',
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    # Restore NOT NULL — safe because no NULLs were ever written
    op.alter_column('user_stories', 'source_connection_id', nullable=False)
    op.alter_column('requirements', 'source_connection_id', nullable=False)
    op.alter_column('impact_analysis', 'source_connection_id', nullable=False)


def downgrade() -> None:
    op.drop_column('source_connections', 'deleted_at')
    op.alter_column('user_stories', 'source_connection_id', nullable=True)
    op.alter_column('requirements', 'source_connection_id', nullable=True)
    op.alter_column('impact_analysis', 'source_connection_id', nullable=True)
