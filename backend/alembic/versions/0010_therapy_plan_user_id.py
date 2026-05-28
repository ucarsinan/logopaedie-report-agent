"""Add ownership to therapy plan records.

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-28
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "therapyplanrecord" not in inspector.get_table_names():
        op.create_table(
            "therapyplanrecord",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("patient_pseudonym", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("report_id", sa.Integer(), sa.ForeignKey("reports.id"), nullable=True),
            sa.Column("plan_data", sa.String(), nullable=False),
            sa.Column(
                "user_id",
                sa.Uuid() if bind.dialect.name == "postgresql" else sa.String(length=36),
                nullable=False,
            ),
        )
        op.create_index("ix_therapyplanrecord_patient_pseudonym", "therapyplanrecord", ["patient_pseudonym"])
        op.create_index("ix_therapyplanrecord_user_id", "therapyplanrecord", ["user_id"])
        return

    column_names = {col["name"] for col in inspector.get_columns("therapyplanrecord")}
    if "user_id" not in column_names:
        user_id_type = sa.Uuid() if bind.dialect.name == "postgresql" else sa.String(length=36)
        with op.batch_alter_table("therapyplanrecord") as batch_op:
            batch_op.add_column(sa.Column("user_id", user_id_type, nullable=True))
            batch_op.create_index("ix_therapyplanrecord_user_id", ["user_id"])

        # Pre-existing rows have no inferrable owner — drop them rather than leak
        # ownership across users. Same conservative approach as migration 0005/0006.
        op.execute("DELETE FROM therapyplanrecord WHERE user_id IS NULL")

        with op.batch_alter_table("therapyplanrecord") as batch_op:
            batch_op.alter_column("user_id", existing_type=user_id_type, nullable=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "therapyplanrecord" not in inspector.get_table_names():
        return

    column_names = {col["name"] for col in inspector.get_columns("therapyplanrecord")}
    if "user_id" not in column_names:
        return

    with op.batch_alter_table("therapyplanrecord") as batch_op:
        index_names = {idx["name"] for idx in inspector.get_indexes("therapyplanrecord")}
        if "ix_therapyplanrecord_user_id" in index_names:
            batch_op.drop_index("ix_therapyplanrecord_user_id")
        batch_op.drop_column("user_id")
