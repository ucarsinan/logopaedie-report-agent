"""Fix audit_log.id column type from varchar to native uuid.

Mirrors 0008 / 0009: conditional ALTER on Postgres only, no-op on SQLite
(the GUID TypeDecorator already stores as CHAR(36) there). audit_log.id is
the smallest-blast-radius pick for the VARCHAR(36) -> UUID alignment audit
(docs/ai/AUDIT_2026-05-29_schema.md) because no other table has an incoming
FK pointing at audit_log.id, so the type swap does not cascade into FK
type-mismatch on Neon. The remaining 12 columns flagged by A3's audit
follow in later migrations once their FK-coordination story is worked out.

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-29
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    inspector = sa.inspect(bind)
    if "audit_log" not in inspector.get_table_names():
        return
    cols = {col["name"]: col for col in inspector.get_columns("audit_log")}

    if "id" in cols and str(cols["id"]["type"]).upper().startswith("VARCHAR"):
        op.execute("ALTER TABLE audit_log ALTER COLUMN id TYPE UUID USING id::uuid")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    inspector = sa.inspect(bind)
    if "audit_log" not in inspector.get_table_names():
        return
    cols = {col["name"]: col for col in inspector.get_columns("audit_log")}

    if "id" in cols:
        op.execute("ALTER TABLE audit_log ALTER COLUMN id TYPE VARCHAR(36) USING id::text")
