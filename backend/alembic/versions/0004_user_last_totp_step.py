"""Add last_totp_step to users for TOTP replay prevention.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-14
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("last_totp_step", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "last_totp_step")
