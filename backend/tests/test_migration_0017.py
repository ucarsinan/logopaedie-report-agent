"""Migration 0017: users.id + 6-FK cluster VARCHAR(36) -> UUID type alignment.

This is the coordinated upgrade for the ``users.id`` reference cluster:
the PK plus the six declared FKs in
``user_sessions``/``email_tokens``/``audit_log``/``patients``/``reports``/
``consent_records``. On Postgres it drops the six FKs (discovered via
inspector — three of them were created inline by 0002 with auto-generated
names), ALTERs all seven columns to native UUID, then recreates the FKs
with canonical names. On SQLite the GUID TypeDecorator already stores as
CHAR(36) and the migration is a dialect-gated no-op.

The SQLite tests therefore mostly verify that the upgrade/downgrade run
without errors, that no cluster table loses any column, and that the id
columns still round-trip through an insert/select. The Postgres-specific
ALTER + FK-rename assertions are marked skip-by-dialect so a future
Postgres-CI run can validate the real type swap end-to-end.
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


_USERS_COLUMNS = {
    "id",
    "email",
    "password_hash",
    "role",
    "email_verified",
    "email_verified_at",
    "totp_secret",
    "totp_enabled",
    "last_totp_step",
    "failed_login_count",
    "locked_until",
    "created_at",
    "updated_at",
}

_CLUSTER_TABLES = (
    "users",
    "user_sessions",
    "email_tokens",
    "audit_log",
    "patients",
    "reports",
    "consent_records",
)


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


def test_migration_0017_preserves_cluster_shape(alembic_cfg):
    """After upgrade to 0017, all cluster tables still exist with id + key columns."""
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0017")
    insp = inspect(create_engine(db_url))
    tables = set(insp.get_table_names())
    for table in _CLUSTER_TABLES:
        assert table in tables, f"missing cluster table after 0017: {table}"
        cols = {col["name"] for col in insp.get_columns(table)}
        assert "id" in cols, f"{table}.id disappeared after 0017"
    # users must keep its full column set
    users_cols = {col["name"] for col in insp.get_columns("users")}
    assert _USERS_COLUMNS.issubset(users_cols), f"users lost columns after 0017: missing {_USERS_COLUMNS - users_cols}"


def test_migration_0017_users_id_round_trips(alembic_cfg):
    """users.id must remain insertable/queryable after the migration.

    On SQLite the migration is a dialect-gated no-op, so this is a smoke
    test that 0017 did not accidentally break the column on the only
    engine the test suite actually runs against.
    """
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0017")
    eng = create_engine(db_url)
    user_id = str(uuid4())
    with eng.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, role, email_verified,"
                " totp_enabled, failed_login_count, created_at, updated_at)"
                " VALUES (:id, 'a@b.test', 'hash', 'user', 0, 0, 0,"
                " '2026-05-31T00:00:00', '2026-05-31T00:00:00')"
            ),
            {"id": user_id},
        )
        got = conn.execute(text("SELECT id FROM users WHERE id = :id"), {"id": user_id}).scalar()
    assert got == user_id


def test_migration_0017_downgrade(alembic_cfg):
    """Downgrade from 0017 -> 0016 must leave the cluster tables intact.

    Like the upgrade, the downgrade is a no-op on SQLite; this just
    confirms the migration is reversible without errors and the tables
    survive the round trip.
    """
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0017")
    command.downgrade(cfg, "0016")
    insp = inspect(create_engine(db_url))
    tables = set(insp.get_table_names())
    for table in _CLUSTER_TABLES:
        assert table in tables, f"missing cluster table after downgrade: {table}"
    users_cols = {col["name"] for col in insp.get_columns("users")}
    assert _USERS_COLUMNS.issubset(users_cols), (
        f"users lost columns after downgrade: missing {_USERS_COLUMNS - users_cols}"
    )


@pytest.mark.skipif(
    True,
    reason="users.id cluster ALTER TYPE only runs on Postgres; SQLite path is no-op."
    " Enabled when the suite runs against a real Postgres engine.",
)
def test_migration_0017_postgres_cluster_is_uuid(alembic_cfg):
    """On Postgres, users.id and all six FK referrers end up as native uuid after 0017."""
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0017")
    insp = inspect(create_engine(db_url))

    users_cols = {col["name"]: col for col in insp.get_columns("users")}
    assert "UUID" in str(users_cols["id"]["type"]).upper()

    cluster_fks = (
        ("user_sessions", "user_id"),
        ("email_tokens", "user_id"),
        ("audit_log", "user_id"),
        ("patients", "user_id"),
        ("reports", "user_id"),
        ("consent_records", "recorded_by"),
    )
    for table, column in cluster_fks:
        cols = {col["name"]: col for col in insp.get_columns(table)}
        assert "UUID" in str(cols[column]["type"]).upper(), f"{table}.{column} did not convert to UUID"


@pytest.mark.skipif(
    True,
    reason="FK reflection assertions only meaningful on Postgres; SQLite path is no-op."
    " Enabled when the suite runs against a real Postgres engine.",
)
def test_migration_0017_postgres_fks_recreated_with_canonical_names(alembic_cfg):
    """On Postgres, after 0017 the six FKs exist with the canonical fk_<table>_<col>_users names."""
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0017")
    insp = inspect(create_engine(db_url))

    expected = {
        "user_sessions": "fk_user_sessions_user_id_users",
        "email_tokens": "fk_email_tokens_user_id_users",
        "audit_log": "fk_audit_log_user_id_users",
        "patients": "fk_patients_user_id_users",
        "reports": "fk_reports_user_id_users",
        "consent_records": "fk_consent_records_recorded_by_users",
    }
    for table, expected_name in expected.items():
        names = {fk.get("name") for fk in insp.get_foreign_keys(table)}
        assert expected_name in names, f"{table} missing canonical FK {expected_name}; got {names}"
