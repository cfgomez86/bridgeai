"""clerk_to_auth0

Revision ID: b7e4f3a2c910
Revises: a3f9d2c1b845
Create Date: 2026-04-23 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "b7e4f3a2c910"
down_revision: Union[str, None] = "a3f9d2c1b845"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("tenants", "clerk_user_id", new_column_name="auth0_user_id")
    op.drop_constraint("uq_tenants_clerk_user_id", "tenants", type_="unique")
    op.create_unique_constraint("uq_tenants_auth0_user_id", "tenants", ["auth0_user_id"])

    op.alter_column("users", "clerk_user_id", new_column_name="auth0_user_id")
    op.drop_constraint("users_clerk_user_id_key", "users", type_="unique")
    op.create_unique_constraint("uq_users_auth0_user_id", "users", ["auth0_user_id"])


def downgrade() -> None:
    op.drop_constraint("uq_users_auth0_user_id", "users", type_="unique")
    op.alter_column("users", "auth0_user_id", new_column_name="clerk_user_id")
    op.create_unique_constraint("users_clerk_user_id_key", "users", ["clerk_user_id"])

    op.drop_constraint("uq_tenants_auth0_user_id", "tenants", type_="unique")
    op.alter_column("tenants", "auth0_user_id", new_column_name="clerk_user_id")
    op.create_unique_constraint("uq_tenants_clerk_user_id", "tenants", ["auth0_user_id"])
