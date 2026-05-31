"""Fix consent_records.id column type from varchar to native uuid.

Mirrors 0013 / 0014 / 0015: conditional ALTER on Postgres only, no-op on
SQLite (the GUID TypeDecorator already stores as CHAR(36) there).
consent_records.id is the fourth target of the VARCHAR(36) -> UUID
alignment audit (docs/ai/AUDIT_2026-05-29_schema.md) and is safe to flip
independently because no other table holds an FK pointing at
consent_records.id (the table itself has only outgoing FKs to patients.id
and users.id). The remaining VARCHAR(36) columns flagged by A3's audit
follow in later migrations once their FK-coordination story is worked
out.

Revision ID: 0016
Revises: 0015
Create Date: 2026-05-31
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    inspector = sa.inspect(bind)
    if "consent_records" not in inspector.get_table_names():
        return
    cols = {col["name"]: col for col in inspector.get_columns("consent_records")}

    if "id" in cols and str(cols["id"]["type"]).upper().startswith("VARCHAR"):
        op.execute("ALTER TABLE consent_records ALTER COLUMN id TYPE UUID USING id::uuid")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    inspector = sa.inspect(bind)
    if "consent_records" not in inspector.get_table_names():
        return
    cols = {col["name"]: col for col in inspector.get_columns("consent_records")}

    if "id" in cols:
        op.execute("ALTER TABLE consent_records ALTER COLUMN id TYPE VARCHAR(36) USING id::text")
