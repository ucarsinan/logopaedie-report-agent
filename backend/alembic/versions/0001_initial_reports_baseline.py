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
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("report_type", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("patient_name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reports_created_at", "reports", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_reports_created_at", table_name="reports")
    op.drop_table("reports")
