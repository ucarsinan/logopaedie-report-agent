"""Add ownership to SOAP records.

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-03
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "soaprecord" not in inspector.get_table_names():
        op.create_table(
            "soaprecord",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("report_id", sa.Integer(), nullable=True),
            sa.Column("session_id", sa.String(), nullable=True),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("subjective", sa.String(), nullable=False),
            sa.Column("objective", sa.String(), nullable=False),
            sa.Column("assessment", sa.String(), nullable=False),
            sa.Column("plan", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_soaprecord_report_id", "soaprecord", ["report_id"])
        op.create_index("ix_soaprecord_session_id", "soaprecord", ["session_id"])
        op.create_index("ix_soaprecord_user_id", "soaprecord", ["user_id"])
        return

    column_names = {col["name"] for col in inspector.get_columns("soaprecord")}
    if "user_id" not in column_names:
        with op.batch_alter_table("soaprecord") as batch_op:
            batch_op.add_column(sa.Column("user_id", sa.String(length=36), nullable=True))
            batch_op.create_index("ix_soaprecord_user_id", ["user_id"])

    op.execute(
        """
        UPDATE soaprecord
        SET user_id = (
            SELECT reports.user_id
            FROM reports
            WHERE reports.id = soaprecord.report_id
        )
        WHERE report_id IS NOT NULL
        """
    )
    op.execute("DELETE FROM soaprecord WHERE user_id IS NULL")

    with op.batch_alter_table("soaprecord") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.String(length=36), nullable=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "soaprecord" not in inspector.get_table_names():
        return

    column_names = {col["name"] for col in inspector.get_columns("soaprecord")}
    if "user_id" not in column_names:
        return

    with op.batch_alter_table("soaprecord") as batch_op:
        index_names = {idx["name"] for idx in inspector.get_indexes("soaprecord")}
        if "ix_soaprecord_user_id" in index_names:
            batch_op.drop_index("ix_soaprecord_user_id")
        batch_op.drop_column("user_id")
