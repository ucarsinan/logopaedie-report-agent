"""Add composite indexes for hot list-query paths.

Covers:
- GET /reports               — ORDER BY created_at DESC scoped to user_id
- GET /reports?patient_id=…  — JOIN/WHERE on reports.patient_id
- GET /patients              — active rows scoped to user_id, newest first
- GET /therapy-plans         — newest first, scoped to user_id

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-29
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_postgres = bind.dialect.name == "postgresql"

    def _existing_indexes(table: str) -> set[str]:
        if table not in inspector.get_table_names():
            return set()
        return {ix["name"] for ix in inspector.get_indexes(table)}

    reports_indexes = _existing_indexes("reports")
    if "reports" in inspector.get_table_names():
        if "idx_reports_user_created" not in reports_indexes:
            op.create_index(
                "idx_reports_user_created",
                "reports",
                ["user_id", sa.text("created_at DESC")],
            )
        if "idx_reports_patient_id" not in reports_indexes:
            op.create_index("idx_reports_patient_id", "reports", ["patient_id"])

    patients_indexes = _existing_indexes("patients")
    if "patients" in inspector.get_table_names() and "idx_patients_user_active" not in patients_indexes:
        # Postgres supports partial indexes; SQLite supports them too but with
        # a different syntax via the postgresql_where kwarg, so fall back to a
        # plain composite for SQLite to keep the migration portable.
        if is_postgres:
            op.create_index(
                "idx_patients_user_active",
                "patients",
                ["user_id", sa.text("created_at DESC")],
                postgresql_where=sa.text("deleted_at IS NULL"),
            )
        else:
            op.create_index(
                "idx_patients_user_active",
                "patients",
                ["user_id", sa.text("created_at DESC")],
            )

    plans_indexes = _existing_indexes("therapyplanrecord")
    if "therapyplanrecord" in inspector.get_table_names() and "idx_therapyplanrecord_user_created" not in plans_indexes:
        op.create_index(
            "idx_therapyplanrecord_user_created",
            "therapyplanrecord",
            ["user_id", sa.text("created_at DESC")],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    def _existing_indexes(table: str) -> set[str]:
        if table not in inspector.get_table_names():
            return set()
        return {ix["name"] for ix in inspector.get_indexes(table)}

    plans_indexes = _existing_indexes("therapyplanrecord")
    if "idx_therapyplanrecord_user_created" in plans_indexes:
        op.drop_index("idx_therapyplanrecord_user_created", table_name="therapyplanrecord")

    patients_indexes = _existing_indexes("patients")
    if "idx_patients_user_active" in patients_indexes:
        op.drop_index("idx_patients_user_active", table_name="patients")

    reports_indexes = _existing_indexes("reports")
    if "idx_reports_patient_id" in reports_indexes:
        op.drop_index("idx_reports_patient_id", table_name="reports")
    if "idx_reports_user_created" in reports_indexes:
        op.drop_index("idx_reports_user_created", table_name="reports")
