"""Coordinated VARCHAR(36) -> UUID conversion for the users.id reference cluster.

Continues the type-alignment chain started by 0013 (audit_log.id), 0014
(email_tokens.id), 0015 (user_sessions.id) and 0016 (consent_records.id).
Those four predecessors were leaf primary keys with no incoming FK pressure
and could each flip independently. ``users.id`` is the opposite case: it
is the PK target of six declared FKs across the schema, so the type swap
must drop those FKs, ALTER all seven columns (PK + 6 referrers) in lock-
step, then recreate the FKs with the same ON DELETE actions.

Conditional on Postgres and a no-op on SQLite (the GUID TypeDecorator
already stores as CHAR(36) there). SOAP/therapy-plan ``user_id`` columns
are already native UUID (per 0009 and 0010) and are intentionally out of
scope: this migration only handles the six VARCHAR(36) FK columns flagged
by docs/ai/AUDIT_2026-05-29_schema.md under "Type encoding drift".

FK discovery is done via ``inspector.get_foreign_keys`` because the three
FKs that 0002 created inline (user_sessions.user_id, email_tokens.user_id,
audit_log.user_id) have no explicit ``name=`` arg, so Postgres assigned
auto-generated names like ``user_sessions_user_id_fkey``. We never
hardcode those names; we always look them up by (constrained_columns,
referred_table) and drop them by their actual reflected name. The three
FKs that 0012 created (patients.user_id, reports.user_id,
consent_records.recorded_by) do have stable explicit names, but we use
the same discovery path for them too so the migration stays idempotent
against any environment where the names ever drift.

After the type swap we recreate the six FKs with explicit names so the
post-state is canonical across all environments (the 0002 inline FKs end
up renamed to ``fk_<table>_<column>_<referred>`` after this migration —
matching the naming convention already used by 0012).

Revision ID: 0017
Revises: 0016
Create Date: 2026-05-31
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


# (table, column, referred_table, referred_column, ondelete, post_name)
# `post_name` is the canonical name we want the FK to have *after* this
# migration runs. We do not assume any FK currently uses this name (the
# three created inline by 0002 don't); we just drop whatever is there by
# its reflected name and recreate with this canonical one.
_FK_SPECS: list[tuple[str, str, str, str, str, str]] = [
    ("user_sessions", "user_id", "users", "id", "CASCADE", "fk_user_sessions_user_id_users"),
    ("email_tokens", "user_id", "users", "id", "CASCADE", "fk_email_tokens_user_id_users"),
    ("audit_log", "user_id", "users", "id", "SET NULL", "fk_audit_log_user_id_users"),
    ("patients", "user_id", "users", "id", "CASCADE", "fk_patients_user_id_users"),
    ("reports", "user_id", "users", "id", "CASCADE", "fk_reports_user_id_users"),
    (
        "consent_records",
        "recorded_by",
        "users",
        "id",
        "RESTRICT",
        "fk_consent_records_recorded_by_users",
    ),
]


def _find_fk_name(inspector: sa.Inspector, table: str, column: str, referred_table: str) -> str | None:
    """Return the actual reflected name of the FK (col -> referred_table) on `table`.

    Returns None if no such FK exists. Necessary because 0002 created its FKs
    inline without explicit names, so we can't hardcode them.
    """
    if table not in inspector.get_table_names():
        return None
    for fk in inspector.get_foreign_keys(table):
        cols = fk.get("constrained_columns") or []
        if cols and cols[0] == column and fk.get("referred_table", "") == referred_table:
            return fk.get("name")
    return None


def _column_is_varchar(inspector: sa.Inspector, table: str, column: str) -> bool:
    if table not in inspector.get_table_names():
        return False
    for col in inspector.get_columns(table):
        if col["name"] == column:
            return str(col["type"]).upper().startswith("VARCHAR")
    return False


def _column_is_uuid(inspector: sa.Inspector, table: str, column: str) -> bool:
    if table not in inspector.get_table_names():
        return False
    for col in inspector.get_columns(table):
        if col["name"] == column:
            return "UUID" in str(col["type"]).upper()
    return False


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    inspector = sa.inspect(bind)

    if "users" not in inspector.get_table_names():
        return

    # Skip if users.id is already UUID (idempotent re-run safety).
    if not _column_is_varchar(inspector, "users", "id"):
        return

    # 1. Drop every existing FK that points at users.id from the six cluster
    #    tables. Discover names via inspector to handle the 0002 inline FKs
    #    whose Postgres-default names we don't want to hardcode.
    for table, column, referred_table, _ref_col, _ondelete, _post_name in _FK_SPECS:
        existing_name = _find_fk_name(inspector, table, column, referred_table)
        if existing_name is not None:
            op.drop_constraint(existing_name, table, type_="foreignkey")

    # 2. ALTER TYPE on users.id (PK) first, then each FK column. Order matters
    #    only logically — Postgres allows either order once the FKs are gone.
    #    Use op.execute for the explicit USING clause; op.alter_column may not
    #    emit it reliably for cross-type conversions.
    op.execute("ALTER TABLE users ALTER COLUMN id TYPE UUID USING id::uuid")
    for table, column, _ref_table, _ref_col, _ondelete, _post_name in _FK_SPECS:
        if _column_is_varchar(inspector, table, column):
            op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE UUID USING {column}::uuid")

    # 3. Recreate the six FKs with canonical names matching the 0012
    #    convention. Same ON DELETE actions as the originals.
    for table, column, ref_table, ref_col, ondelete, post_name in _FK_SPECS:
        op.create_foreign_key(
            post_name,
            table,
            ref_table,
            [column],
            [ref_col],
            ondelete=ondelete,
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    inspector = sa.inspect(bind)

    if "users" not in inspector.get_table_names():
        return

    # Skip if users.id is already VARCHAR (idempotent reverse).
    if not _column_is_uuid(inspector, "users", "id"):
        return

    # Reverse order: drop FKs, ALTER back to VARCHAR(36), recreate FKs with
    # the canonical names so the downgrade-state matches what the upgrade
    # produced for the post-FK naming.
    for table, column, referred_table, _ref_col, _ondelete, _post_name in _FK_SPECS:
        existing_name = _find_fk_name(inspector, table, column, referred_table)
        if existing_name is not None:
            op.drop_constraint(existing_name, table, type_="foreignkey")

    for table, column, _ref_table, _ref_col, _ondelete, _post_name in _FK_SPECS:
        if _column_is_uuid(inspector, table, column):
            op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE VARCHAR(36) USING {column}::text")
    op.execute("ALTER TABLE users ALTER COLUMN id TYPE VARCHAR(36) USING id::text")

    for table, column, ref_table, ref_col, ondelete, post_name in _FK_SPECS:
        op.create_foreign_key(
            post_name,
            table,
            ref_table,
            [column],
            [ref_col],
            ondelete=ondelete,
        )
