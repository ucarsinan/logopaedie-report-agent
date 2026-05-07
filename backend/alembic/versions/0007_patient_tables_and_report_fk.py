"""Add patient tables and reports.patient_id FK.

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-07
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "patients" not in tables:
        op.create_table(
            "patients",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("system_id", sa.String(), nullable=False),
            sa.Column("pseudonym", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("realname_enc", sa.LargeBinary(), nullable=False),
            sa.Column("birthdate_enc", sa.LargeBinary(), nullable=False),
            sa.Column("phone_enc", sa.LargeBinary(), nullable=True),
            sa.Column("email_enc", sa.LargeBinary(), nullable=True),
            sa.Column("insurance_nr_enc", sa.LargeBinary(), nullable=True),
            sa.Column("gender", sa.String(), nullable=True),
            sa.Column("age_group", sa.String(), nullable=False, server_default="erwachsen"),
            sa.Column("icd10_codes", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("disorder_text", sa.String(), nullable=False, server_default=""),
            sa.Column("indikationsschluessel", sa.String(), nullable=False, server_default=""),
            sa.Column("insurance_type", sa.String(), nullable=True),
            sa.Column("insurance_name", sa.String(), nullable=True),
            sa.Column("guardian_name", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_patients_user_id", "patients", ["user_id"])
        op.create_index("ix_patients_system_id", "patients", ["system_id"], unique=True)

    if "consent_records" not in tables:
        op.create_table(
            "consent_records",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("patient_id", sa.String(length=36), nullable=False),
            sa.Column("consent_type", sa.String(), nullable=False),
            sa.Column("granted", sa.Boolean(), nullable=False),
            sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("recorded_by", sa.String(length=36), nullable=False),
        )
        op.create_index("ix_consent_records_patient_id", "consent_records", ["patient_id"])

    # Add patient_id to reports if missing
    report_cols = {col["name"] for col in inspector.get_columns("reports")}
    if "patient_id" not in report_cols:
        with op.batch_alter_table("reports") as batch_op:
            batch_op.add_column(sa.Column("patient_id", sa.String(length=36), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    report_cols = {col["name"] for col in inspector.get_columns("reports")}
    if "patient_id" in report_cols:
        with op.batch_alter_table("reports") as batch_op:
            batch_op.drop_column("patient_id")

    if "consent_records" in inspector.get_table_names():
        op.drop_table("consent_records")

    if "patients" in inspector.get_table_names():
        op.drop_table("patients")
