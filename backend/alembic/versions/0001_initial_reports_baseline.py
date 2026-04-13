"""initial reports baseline

Revision ID: 0001
Revises:
Create Date: 2026-04-13
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("pseudonym", sa.String(), nullable=False),
        sa.Column("report_type", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_json", sa.Text(), nullable=False),
    )
    op.create_index("ix_reports_pseudonym", "reports", ["pseudonym"])


def downgrade() -> None:
    op.drop_index("ix_reports_pseudonym", table_name="reports")
    op.drop_table("reports")
