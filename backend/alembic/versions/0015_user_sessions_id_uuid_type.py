"""Fix user_sessions.id column type from varchar to native uuid.

Third in the VARCHAR(36) -> UUID type-alignment chain started by 0013
(audit_log.id) and continued by 0014 (email_tokens.id). Like its
predecessors, this migration is conditional on Postgres and a no-op on
SQLite (the GUID TypeDecorator already stores as CHAR(36) there).

Pre-flight FK audit (see docs/ai/AUDIT_2026-05-29_schema.md, "Type
encoding drift"): `user_sessions.id` is a leaf primary key. There is no
self-referential column (no parent_id / replaced_by) on user_sessions
and no other table in the schema declares an incoming FK that references
user_sessions.id. The only FK on the table is OUTGOING
(user_sessions.user_id -> users.id), and that column's type alignment is
out of scope for this migration (users.id is still VARCHAR(36) on Neon
and will be aligned in a later coordinated migration that touches both
sides simultaneously). Therefore the type swap can run in isolation
without dropping or recreating any FK constraint.

The remaining columns flagged by A3's audit follow in later migrations
once their FK-coordination story is worked out.

Revision ID: 0015
Revises: 0014
Create Date: 2026-05-31
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    inspector = sa.inspect(bind)
    if "user_sessions" not in inspector.get_table_names():
        return
    cols = {col["name"]: col for col in inspector.get_columns("user_sessions")}

    if "id" in cols and str(cols["id"]["type"]).upper().startswith("VARCHAR"):
        op.execute("ALTER TABLE user_sessions ALTER COLUMN id TYPE UUID USING id::uuid")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    inspector = sa.inspect(bind)
    if "user_sessions" not in inspector.get_table_names():
        return
    cols = {col["name"]: col for col in inspector.get_columns("user_sessions")}

    if "id" in cols:
        op.execute("ALTER TABLE user_sessions ALTER COLUMN id TYPE VARCHAR(36) USING id::text")
