"""Coordinated VARCHAR(36) -> UUID type alignment for the patients.id cluster.

Fifth (and largest so far) in the type-encoding-drift chain started by 0013
(audit_log.id) and continued by 0014 (email_tokens.id), 0015 (user_sessions.id),
and 0016 (consent_records.id). Unlike its leaf-PK predecessors, patients.id has
incoming FKs from two other tables, so a naive ALTER on the PK fails on Postgres
with "foreign key constraint depends on column".

This migration coordinates:

1. `patients.id` (PK)               VARCHAR(36) -> UUID
2. `consent_records.patient_id`     VARCHAR(36) -> UUID  (FK -> patients.id, CASCADE)

The cluster also includes `reports.patient_id`, which is **already UUID** as of
migration 0008 (it was the first patient_id type alignment, landed long before
the FK constraints were formalized). However, 0012 added
`fk_reports_patient_id_patients` on top of that already-UUID column. Postgres
still refuses to ALTER the referenced PK type while a dependent FK exists, even
when the types happen to already match — the planner does not constant-fold
"VARCHAR(36) -> UUID is a no-op for a column that is already UUID". So we drop
and recreate that FK too, with the same name and ondelete=SET NULL behavior it
was given in 0012.

Postgres-only conversion; SQLite is a no-op (the GUID TypeDecorator already
stores as CHAR(36) there). FK names and ondelete behavior are discovered from
the live inspector rather than hardcoded, so the migration is robust against
environments where 0012 was applied with a different naming scheme (e.g. an old
manual Neon hotfix). Recreation falls back to the canonical names + behavior
from 0012 when the live FK is missing entirely.

Depends on 0017 (users.id cluster) being merged first. The two cluster
migrations were authored in parallel worktrees and must land in chain order.

Revision ID: 0018
Revises: 0017
Create Date: 2026-05-31
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


# Canonical FK specs (matches 0012). Used when we have to recreate a missing FK
# or after the type swap on upgrade/downgrade.
# (table, column, fk_name, ondelete)
_INCOMING_FKS: list[tuple[str, str, str, str]] = [
    ("consent_records", "patient_id", "fk_consent_records_patient_id_patients", "CASCADE"),
    ("reports", "patient_id", "fk_reports_patient_id_patients", "SET NULL"),
]


def _find_fk_to_patients(inspector: sa.Inspector, table: str, column: str) -> dict[str, Any] | None:
    """Return the FK dict for `table.column -> patients.id`, or None if absent."""
    if table not in inspector.get_table_names():
        return None
    for fk in inspector.get_foreign_keys(table):
        if fk.get("referred_table") != "patients":
            continue
        cols = fk.get("constrained_columns") or []
        if column in cols:
            return dict(fk)
    return None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    inspector = sa.inspect(bind)

    if "patients" not in inspector.get_table_names():
        return

    patients_id_col = next((c for c in inspector.get_columns("patients") if c["name"] == "id"), None)
    if patients_id_col is None or not str(patients_id_col["type"]).upper().startswith("VARCHAR"):
        # Already converted (or never existed in this shape) — nothing to do.
        return

    # 1. Discover live FK names so we drop the actual constraint, not a guessed name.
    dropped: list[tuple[str, str, str, str]] = []  # (table, column, fk_name, ondelete)
    for table, column, default_name, default_ondelete in _INCOMING_FKS:
        fk = _find_fk_to_patients(inspector, table, column)
        if fk is None:
            # FK is not present on this environment — record the canonical spec so
            # we still install it after the type swap. This keeps the migration
            # additive in the rare case 0012 was rolled back or partially applied.
            dropped.append((table, column, default_name, default_ondelete))
            continue
        live_name = fk.get("name") or default_name
        live_ondelete = (fk.get("options") or {}).get("ondelete") or default_ondelete
        op.drop_constraint(live_name, table, type_="foreignkey")
        dropped.append((table, column, live_name, live_ondelete))

    # 2. ALTER patients.id from VARCHAR(36) to UUID.
    op.execute("ALTER TABLE patients ALTER COLUMN id TYPE UUID USING id::uuid")

    # 3. ALTER consent_records.patient_id to UUID so the FK can be recreated with
    #    matching types. reports.patient_id is already UUID (since 0008), so it
    #    needs no type change — only its FK is re-attached below.
    if "consent_records" in inspector.get_table_names():
        consent_pid = next(
            (c for c in inspector.get_columns("consent_records") if c["name"] == "patient_id"),
            None,
        )
        if consent_pid is not None and str(consent_pid["type"]).upper().startswith("VARCHAR"):
            op.execute("ALTER TABLE consent_records ALTER COLUMN patient_id TYPE UUID USING patient_id::uuid")

    # 4. Recreate the FKs we dropped (or install canonical ones if they were missing).
    for table, column, fk_name, ondelete in dropped:
        if table not in sa.inspect(bind).get_table_names():
            continue
        op.create_foreign_key(
            fk_name,
            table,
            "patients",
            [column],
            ["id"],
            ondelete=ondelete,
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    inspector = sa.inspect(bind)

    if "patients" not in inspector.get_table_names():
        return

    patients_id_col = next((c for c in inspector.get_columns("patients") if c["name"] == "id"), None)
    if patients_id_col is None:
        return
    # Only downgrade if currently UUID (matches the inverse of the upgrade guard).
    if "UUID" not in str(patients_id_col["type"]).upper():
        return

    # Drop incoming FKs (live names), revert types, recreate FKs.
    dropped: list[tuple[str, str, str, str]] = []
    for table, column, default_name, default_ondelete in _INCOMING_FKS:
        fk = _find_fk_to_patients(inspector, table, column)
        if fk is None:
            dropped.append((table, column, default_name, default_ondelete))
            continue
        live_name = fk.get("name") or default_name
        live_ondelete = (fk.get("options") or {}).get("ondelete") or default_ondelete
        op.drop_constraint(live_name, table, type_="foreignkey")
        dropped.append((table, column, live_name, live_ondelete))

    op.execute("ALTER TABLE patients ALTER COLUMN id TYPE VARCHAR(36) USING id::text")

    if "consent_records" in inspector.get_table_names():
        consent_pid = next(
            (c for c in inspector.get_columns("consent_records") if c["name"] == "patient_id"),
            None,
        )
        if consent_pid is not None and "UUID" in str(consent_pid["type"]).upper():
            op.execute("ALTER TABLE consent_records ALTER COLUMN patient_id TYPE VARCHAR(36) USING patient_id::text")

    # NB: reports.patient_id stays UUID — it was already UUID before this migration
    # ran (since 0008), and downgrading to 0017 should leave 0008's work in place.

    for table, column, fk_name, ondelete in dropped:
        if table not in sa.inspect(bind).get_table_names():
            continue
        op.create_foreign_key(
            fk_name,
            table,
            "patients",
            [column],
            ["id"],
            ondelete=ondelete,
        )
