"""Fix reports.patient_id column type from varchar to native uuid.

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-07
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    inspector = sa.inspect(bind)
    cols = {col["name"]: col for col in inspector.get_columns("reports")}

    if "patient_id" in cols and str(cols["patient_id"]["type"]).upper().startswith("VARCHAR"):
        op.execute("ALTER TABLE reports ALTER COLUMN patient_id TYPE UUID USING patient_id::uuid")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    inspector = sa.inspect(bind)
    cols = {col["name"]: col for col in inspector.get_columns("reports")}

    if "patient_id" in cols:
        op.execute("ALTER TABLE reports ALTER COLUMN patient_id TYPE VARCHAR(36) USING patient_id::text")
