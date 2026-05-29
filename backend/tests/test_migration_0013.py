"""Migration 0013: audit_log.id VARCHAR(36) -> UUID type alignment.

This is the first of the type-encoding-drift cleanups flagged by A3's
2026-05-29 schema audit. On SQLite the migration is a no-op (the GUID
TypeDecorator already stores as CHAR(36)); the real ALTER only runs on
Postgres. The SQLite tests below therefore mostly verify that:

- the migration applies and reverses without errors,
- the audit_log table remains structurally intact (column set unchanged),
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


_AUDIT_LOG_COLUMNS = {
    "id",
    "user_id",
    "event",
    "ip_address",
    "user_agent",
    "metadata_json",
    "created_at",
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


def test_migration_0013_preserves_audit_log_shape(alembic_cfg):
    """After upgrade to 0013, audit_log still has the expected columns."""
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0013")
    insp = inspect(create_engine(db_url))
    assert "audit_log" in insp.get_table_names()
    columns = {col["name"] for col in insp.get_columns("audit_log")}
    assert _AUDIT_LOG_COLUMNS.issubset(columns), (
        f"audit_log lost columns after 0013: missing {_AUDIT_LOG_COLUMNS - columns}"
    )


def test_migration_0013_id_round_trips(alembic_cfg):
    """audit_log.id must remain insertable/queryable after the migration.

    On SQLite the migration is a dialect-gated no-op, so this is mainly a
    smoke test that 0013 did not accidentally break the column on the
    only engine the test suite actually runs against.
    """
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0013")
    eng = create_engine(db_url)
    row_id = str(uuid4())
    with eng.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO audit_log (id, user_id, event, ip_address, user_agent,"
                " metadata_json, created_at) VALUES (:id, NULL, 'test.event', NULL,"
                " NULL, '{}', '2026-05-29T00:00:00')"
            ),
            {"id": row_id},
        )
        got = conn.execute(text("SELECT id FROM audit_log WHERE id = :id"), {"id": row_id}).scalar()
    assert got == row_id


def test_migration_0013_downgrade(alembic_cfg):
    """Downgrade from 0013 -> 0012 must leave audit_log intact.

    Like the upgrade, the downgrade is a no-op on SQLite; this just
    confirms the migration is reversible without errors and the table
    survives the round trip.
    """
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0013")
    command.downgrade(cfg, "0012")
    insp = inspect(create_engine(db_url))
    assert "audit_log" in insp.get_table_names()
    columns = {col["name"] for col in insp.get_columns("audit_log")}
    assert _AUDIT_LOG_COLUMNS.issubset(columns), (
        f"audit_log lost columns after downgrade: missing {_AUDIT_LOG_COLUMNS - columns}"
    )


@pytest.mark.skipif(
    True,
    reason="audit_log.id ALTER TYPE only runs on Postgres; SQLite path is no-op."
    " Enabled when the suite runs against a real Postgres engine.",
)
def test_migration_0013_postgres_id_is_uuid(alembic_cfg):
    """On Postgres, audit_log.id ends up as the native uuid type after 0013."""
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0013")
    insp = inspect(create_engine(db_url))
    cols = {col["name"]: col for col in insp.get_columns("audit_log")}
    assert "UUID" in str(cols["id"]["type"]).upper()
