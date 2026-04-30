"""preserve history on connection delete

Revision ID: a1b2c3d4e5f6
Revises: f3a2b5c1d847
Create Date: 2026-04-30 18:00:00.000000

Make source_connection_id nullable in user_stories, requirements, and
impact_analysis so that deleting a connection only wipes the code index
(code_files, impacted_files) while preserving historical stories,
requirements, analyses, and ticket data.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f3a2b5c1d847'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('user_stories', 'source_connection_id', nullable=True)
    op.alter_column('requirements', 'source_connection_id', nullable=True)
    op.alter_column('impact_analysis', 'source_connection_id', nullable=True)


def downgrade() -> None:
    # Re-applying NOT NULL requires no existing NULLs; guard with a note.
    # In practice downgrade should only be run on a clean dev database.
    op.alter_column('user_stories', 'source_connection_id', nullable=False)
    op.alter_column('requirements', 'source_connection_id', nullable=False)
    op.alter_column('impact_analysis', 'source_connection_id', nullable=False)
