"""user_based_tenancy

Revision ID: a3f9d2c1b845
Revises: e1a62213dda8
Create Date: 2026-04-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a3f9d2c1b845'
down_revision: Union[str, None] = 'e1a62213dda8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Purge all org-based dev data
    op.execute("TRUNCATE tenants CASCADE")

    # Add new clerk_user_id column
    op.add_column('tenants', sa.Column('clerk_user_id', sa.String(255), nullable=False,
                                       server_default='__placeholder__'))
    op.execute("ALTER TABLE tenants ALTER COLUMN clerk_user_id DROP DEFAULT")

    # Drop old org-based columns
    op.drop_constraint('tenants_clerk_org_id_key', 'tenants', type_='unique')
    op.drop_column('tenants', 'clerk_org_id')
    op.drop_constraint('tenants_slug_key', 'tenants', type_='unique')
    op.drop_column('tenants', 'slug')

    op.create_unique_constraint('uq_tenants_clerk_user_id', 'tenants', ['clerk_user_id'])


def downgrade() -> None:
    op.drop_constraint('uq_tenants_clerk_user_id', 'tenants', type_='unique')
    op.drop_column('tenants', 'clerk_user_id')
    op.add_column('tenants', sa.Column('clerk_org_id', sa.String(255), nullable=False))
    op.create_unique_constraint('tenants_clerk_org_id_key', 'tenants', ['clerk_org_id'])
    op.add_column('tenants', sa.Column('slug', sa.String(100), nullable=False))
    op.create_unique_constraint('tenants_slug_key', 'tenants', ['slug'])
