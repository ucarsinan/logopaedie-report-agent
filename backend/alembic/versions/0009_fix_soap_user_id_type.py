"""Fix soaprecord.user_id column type from varchar to native uuid.

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-08
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    inspector = sa.inspect(bind)
    if "soaprecord" not in inspector.get_table_names():
        return
    cols = {col["name"]: col for col in inspector.get_columns("soaprecord")}

    if "user_id" in cols and str(cols["user_id"]["type"]).upper().startswith("VARCHAR"):
        op.execute("ALTER TABLE soaprecord ALTER COLUMN user_id TYPE UUID USING user_id::uuid")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    inspector = sa.inspect(bind)
    if "soaprecord" not in inspector.get_table_names():
        return
    cols = {col["name"]: col for col in inspector.get_columns("soaprecord")}

    if "user_id" in cols:
        op.execute("ALTER TABLE soaprecord ALTER COLUMN user_id TYPE VARCHAR(36) USING user_id::text")
