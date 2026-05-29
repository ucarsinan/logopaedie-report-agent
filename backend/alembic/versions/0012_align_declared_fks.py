"""Align declared FKs across reports, soaprecord, patients, consent_records, therapyplanrecord.

The models in backend/models/*.py declare these FK constraints, but migrations 0005,
0006, 0007 and 0010 only added the underlying columns — never the constraints. On
Neon this means a user delete does not cascade through these tables. Local dev
boots from SQLModel.metadata via create_all and therefore *does* have them, so
this is a dev/prod schema split.

`therapyplanrecord_user_id_fkey` was added to Neon manually as a hotfix on
2026-05-29. The conditional inspector pattern below makes this migration a no-op
against any environment where the FK already exists, so re-running it on Neon
is safe.

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-29
"""

from __future__ import annotations

import contextlib

import sqlalchemy as sa

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


# (table, fk_name, column, referred_table, referred_column, ondelete)
_FK_SPECS: list[tuple[str, str, str, str, str, str]] = [
    ("reports", "fk_reports_user_id_users", "user_id", "users", "id", "CASCADE"),
    ("reports", "fk_reports_patient_id_patients", "patient_id", "patients", "id", "SET NULL"),
    ("soaprecord", "fk_soaprecord_user_id_users", "user_id", "users", "id", "CASCADE"),
    ("patients", "fk_patients_user_id_users", "user_id", "users", "id", "CASCADE"),
    (
        "consent_records",
        "fk_consent_records_patient_id_patients",
        "patient_id",
        "patients",
        "id",
        "CASCADE",
    ),
    (
        "consent_records",
        "fk_consent_records_recorded_by_users",
        "recorded_by",
        "users",
        "id",
        "RESTRICT",
    ),
    (
        "therapyplanrecord",
        "fk_therapyplanrecord_user_id_users",
        "user_id",
        "users",
        "id",
        "CASCADE",
    ),
]


def _existing_fks(inspector: sa.Inspector, table: str) -> set[tuple[str, str]]:
    """Return {(constrained_column, referred_table)} for FKs already on `table`.

    Used to make this migration idempotent: if the constraint is already there
    (e.g. Neon was hotfixed manually, or the table was created by create_all in
    a fresh dev environment), we skip it instead of erroring.
    """
    if table not in inspector.get_table_names():
        return set()
    out: set[tuple[str, str]] = set()
    for fk in inspector.get_foreign_keys(table):
        cols = fk.get("constrained_columns") or []
        if not cols:
            continue
        out.add((cols[0], fk.get("referred_table", "")))
    return out


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    for table, fk_name, column, referred_table, referred_column, ondelete in _FK_SPECS:
        if table not in table_names:
            # Table was never created (e.g. partial downgrade state); skip.
            continue
        if (column, referred_table) in _existing_fks(inspector, table):
            # FK already present — Neon hotfix or fresh create_all dev DB.
            continue
        # batch_alter_table is required on SQLite (it rebuilds the table to add the
        # constraint) and a no-op wrapper on Postgres.
        with op.batch_alter_table(table) as batch_op:
            batch_op.create_foreign_key(
                fk_name,
                referred_table,
                [column],
                [referred_column],
                ondelete=ondelete,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    # Reverse order, drop only what we (or anyone using our naming convention)
    # actually placed there. Swallow errors so a partial environment does not
    # block a downgrade (e.g. SQLite without batch-supported drop_constraint on
    # an FK named by a previous tool). Tests cover the happy path.
    for table, fk_name, *_rest in reversed(_FK_SPECS):
        if table not in table_names:
            continue
        existing_names = {fk.get("name") for fk in inspector.get_foreign_keys(table)}
        if fk_name not in existing_names:
            continue
        with op.batch_alter_table(table) as batch_op, contextlib.suppress(Exception):
            batch_op.drop_constraint(fk_name, type_="foreignkey")
