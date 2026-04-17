"""Add user_id to reports; drop orphaned rows (no ownership can be inferred).

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-14
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Clear orphaned reports — they cannot be assigned to any user
    op.execute("DELETE FROM reports")

    # Add user_id as NOT NULL via batch (SQLite-safe: table is recreated internally)
    # FK is enforced at ORM level; omitting named constraint here for cross-DB compat
    with op.batch_alter_table("reports", recreate="always") as batch_op:
        batch_op.add_column(
            sa.Column(
                "user_id",
                sa.String(length=36),
                nullable=False,
                server_default="",  # satisfies NOT NULL during ALTER; table is empty
            )
        )
        batch_op.alter_column("user_id", server_default=None, nullable=False)
        batch_op.create_index("ix_reports_user_id", ["user_id"])


def downgrade() -> None:
    with op.batch_alter_table("reports") as batch_op:
        batch_op.drop_index("ix_reports_user_id")
        batch_op.drop_column("user_id")
