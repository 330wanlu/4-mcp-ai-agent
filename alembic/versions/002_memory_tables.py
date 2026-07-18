"""memory: session_summaries + user_preferences

Revision ID: 002_memory
Revises: 001_initial
Create Date: 2026-07-18

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_memory"
down_revision: Union[str, Sequence[str], None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session_summaries",
        sa.Column("session_id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("summary", sa.Text(), server_default=""),
        sa.Column("turns", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("meta", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_session_summaries_user_id", "session_summaries", ["user_id"])

    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.String(length=64), primary_key=True),
        sa.Column(
            "preferences",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("notes", sa.Text(), server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("user_preferences")
    op.drop_index("ix_session_summaries_user_id", table_name="session_summaries")
    op.drop_table("session_summaries")
