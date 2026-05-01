"""track models and calls per pipeline step

Adds tracking columns so each step (coherence judge, requirement parser,
story generator) records which model evaluated it and how many provider
calls were spent (retries + AC repair count toward `generator_calls`).
The story_quality_score table already tracks this via judge_model and
samples_used — no change needed there.

Revision ID: f9c4a2e7b138
Revises: a7d2e9f1b463
Create Date: 2026-05-01 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "f9c4a2e7b138"
down_revision: Union[str, Sequence[str], None] = "a7d2e9f1b463"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    req_cols = {c["name"] for c in inspector.get_columns("requirements")}
    if "coherence_model" not in req_cols:
        op.add_column(
            "requirements",
            sa.Column("coherence_model", sa.String(length=120), nullable=True),
        )
    if "coherence_calls" not in req_cols:
        op.add_column(
            "requirements",
            sa.Column(
                "coherence_calls",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )
    if "parser_model" not in req_cols:
        op.add_column(
            "requirements",
            sa.Column("parser_model", sa.String(length=120), nullable=True),
        )
    if "parser_calls" not in req_cols:
        op.add_column(
            "requirements",
            sa.Column(
                "parser_calls",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )

    story_cols = {c["name"] for c in inspector.get_columns("user_stories")}
    if "generator_calls" not in story_cols:
        op.add_column(
            "user_stories",
            sa.Column(
                "generator_calls",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    story_cols = {c["name"] for c in inspector.get_columns("user_stories")}
    if "generator_calls" in story_cols:
        op.drop_column("user_stories", "generator_calls")

    req_cols = {c["name"] for c in inspector.get_columns("requirements")}
    for col in ("parser_calls", "parser_model", "coherence_calls", "coherence_model"):
        if col in req_cols:
            op.drop_column("requirements", col)
