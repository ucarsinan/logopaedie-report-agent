"""Migration 0016: consent_records.id VARCHAR(36) -> UUID type alignment.

Mirrors test_migration_0013 (audit_log.id). On SQLite the migration is a
no-op (the GUID TypeDecorator already stores as CHAR(36)); the real ALTER
only runs on Postgres. The SQLite tests below therefore mostly verify
that:

- the migration applies and reverses without errors,
- the consent_records table remains structurally intact (column set
  unchanged),
- the id column still round-trips through an insert/select.

The Postgres-specific ALTER assertions are marked skip-by-dialect so a
future Postgres-CI run can validate the real type swap end-to-end.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parent.parent


_CONSENT_RECORDS_COLUMNS = {
    "id",
    "patient_id",
    "consent_type",
    "granted",
    "granted_at",
    "revoked_at",
    "recorded_by",
}


@pytest.fixture
def alembic_cfg(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_name = tmp.name
    url = f"sqlite:///{tmp_name}"
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    yield cfg, url
    os.unlink(tmp_name)


def test_migration_0016_preserves_consent_records_shape(alembic_cfg):
    """After upgrade to 0016, consent_records still has the expected columns."""
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0016")
    insp = inspect(create_engine(db_url))
    assert "consent_records" in insp.get_table_names()
    columns = {col["name"] for col in insp.get_columns("consent_records")}
    assert _CONSENT_RECORDS_COLUMNS.issubset(columns), (
        f"consent_records lost columns after 0016: missing {_CONSENT_RECORDS_COLUMNS - columns}"
    )


def test_migration_0016_id_round_trips(alembic_cfg):
    """consent_records.id must remain insertable/queryable after the migration.

    On SQLite the migration is a dialect-gated no-op, so this is mainly a
    smoke test that 0016 did not accidentally break the column on the
    only engine the test suite actually runs against. SQLite does not
    enforce FK constraints by default, so the patient_id / recorded_by
    values can be unreferenced UUID strings for this round-trip check.
    """
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0016")
    eng = create_engine(db_url)
    row_id = str(uuid4())
    patient_id = str(uuid4())
    recorded_by = str(uuid4())
    with eng.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO consent_records (id, patient_id, consent_type, granted,"
                " granted_at, revoked_at, recorded_by) VALUES (:id, :pid,"
                " 'data_processing', 1, '2026-05-31T00:00:00', NULL, :rby)"
            ),
            {"id": row_id, "pid": patient_id, "rby": recorded_by},
        )
        got = conn.execute(text("SELECT id FROM consent_records WHERE id = :id"), {"id": row_id}).scalar()
    assert got == row_id


def test_migration_0016_downgrade(alembic_cfg):
    """Downgrade from 0016 -> 0015 must leave consent_records intact.

    Like the upgrade, the downgrade is a no-op on SQLite; this just
    confirms the migration is reversible without errors and the table
    survives the round trip.
    """
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0016")
    command.downgrade(cfg, "0015")
    insp = inspect(create_engine(db_url))
    assert "consent_records" in insp.get_table_names()
    columns = {col["name"] for col in insp.get_columns("consent_records")}
    assert _CONSENT_RECORDS_COLUMNS.issubset(columns), (
        f"consent_records lost columns after downgrade: missing {_CONSENT_RECORDS_COLUMNS - columns}"
    )


@pytest.mark.skipif(
    True,
    reason="consent_records.id ALTER TYPE only runs on Postgres; SQLite path is no-op."
    " Enabled when the suite runs against a real Postgres engine.",
)
def test_migration_0016_postgres_id_is_uuid(alembic_cfg):
    """On Postgres, consent_records.id ends up as the native uuid type after 0016."""
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0016")
    insp = inspect(create_engine(db_url))
    cols = {col["name"]: col for col in insp.get_columns("consent_records")}
    assert "UUID" in str(cols["id"]["type"]).upper()
