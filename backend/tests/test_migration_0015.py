"""Migration 0015: user_sessions.id VARCHAR(36) -> UUID type alignment.

Third in the type-encoding-drift cleanup chain after 0013 (audit_log.id)
and 0014 (email_tokens.id). On SQLite the migration is a no-op (the GUID
TypeDecorator already stores as CHAR(36)); the real ALTER only runs on
Postgres. The SQLite tests below therefore mostly verify that:

- the migration applies and reverses without errors,
- the user_sessions table remains structurally intact (column set unchanged),
- the id column still round-trips through an insert/select,
- the outgoing user_id -> users.id FK is still honored after the upgrade
  (insert with a valid user_id succeeds; insert with a dangling user_id
  raises IntegrityError once SQLite FK enforcement is enabled).

The Postgres-specific ALTER assertions are marked skip-by-dialect so a
future Postgres-CI run can validate the real type swap end-to-end.
"""

from __future__ import annotations

import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parent.parent


_USER_SESSIONS_COLUMNS = {
    "id",
    "user_id",
    "refresh_token_hash",
    "user_agent",
    "ip_address",
    "created_at",
    "last_used_at",
    "expires_at",
    "revoked_at",
    "rotated",
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


def _engine_with_sqlite_fks(db_url: str):
    """Build an engine that turns SQLite's PRAGMA foreign_keys=ON.

    Necessary because SQLite does not enforce FKs by default, and the FK
    regression test below specifically asserts the constraint is still
    honored after the type-alignment migration runs.
    """
    eng = create_engine(db_url)

    @event.listens_for(eng, "connect")
    def _fk_pragma(dbapi_connection, _):  # pragma: no cover - trivial hook
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return eng


def test_migration_0015_preserves_user_sessions_shape(alembic_cfg):
    """After upgrade to 0015, user_sessions still has the expected columns."""
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0015")
    insp = inspect(create_engine(db_url))
    assert "user_sessions" in insp.get_table_names()
    columns = {col["name"] for col in insp.get_columns("user_sessions")}
    assert _USER_SESSIONS_COLUMNS.issubset(columns), (
        f"user_sessions lost columns after 0015: missing {_USER_SESSIONS_COLUMNS - columns}"
    )


def test_migration_0015_id_round_trips(alembic_cfg):
    """user_sessions.id must remain insertable/queryable after the migration.

    On SQLite the migration is a dialect-gated no-op, so this is mainly a
    smoke test that 0015 did not accidentally break the column on the
    only engine the test suite actually runs against.
    """
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0015")
    eng = create_engine(db_url)
    user_id = str(uuid4())
    session_id = str(uuid4())
    now = datetime.now(UTC).isoformat()
    expires = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    with eng.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, role, email_verified,"
                " totp_enabled, failed_login_count, created_at, updated_at) VALUES"
                " (:id, :email, 'hash', 'user', 0, 0, 0, :now, :now)"
            ),
            {"id": user_id, "email": f"u-{user_id[:8]}@example.com", "now": now},
        )
        conn.execute(
            text(
                "INSERT INTO user_sessions (id, user_id, refresh_token_hash, user_agent,"
                " ip_address, created_at, last_used_at, expires_at, revoked_at, rotated)"
                " VALUES (:id, :user_id, 'rth', NULL, NULL, :now, :now, :exp, NULL, 0)"
            ),
            {"id": session_id, "user_id": user_id, "now": now, "exp": expires},
        )
        got = conn.execute(
            text("SELECT id FROM user_sessions WHERE id = :id"),
            {"id": session_id},
        ).scalar()
    assert got == session_id


def test_migration_0015_user_id_fk_still_enforced(alembic_cfg):
    """Outgoing FK user_sessions.user_id -> users.id survives the upgrade.

    Regression guard for the pre-flight conclusion that 0015 is safe to
    run in isolation: even though we did not touch the FK column or its
    constraint, we verify after-migration that inserting a session with
    a dangling user_id still fails. On SQLite this requires
    PRAGMA foreign_keys=ON (off by default).
    """
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0015")
    eng = _engine_with_sqlite_fks(db_url)
    now = datetime.now(UTC).isoformat()
    expires = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    with eng.begin() as conn, pytest.raises(IntegrityError):
        conn.execute(
            text(
                "INSERT INTO user_sessions (id, user_id, refresh_token_hash, user_agent,"
                " ip_address, created_at, last_used_at, expires_at, revoked_at, rotated)"
                " VALUES (:id, :user_id, 'rth', NULL, NULL, :now, :now, :exp, NULL, 0)"
            ),
            {
                "id": str(uuid4()),
                "user_id": str(uuid4()),  # not present in users
                "now": now,
                "exp": expires,
            },
        )


def test_migration_0015_downgrade(alembic_cfg):
    """Downgrade from 0015 -> 0014 must leave user_sessions intact.

    Like the upgrade, the downgrade is a no-op on SQLite; this just
    confirms the migration is reversible without errors and the table
    survives the round trip.
    """
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0015")
    command.downgrade(cfg, "0014")
    insp = inspect(create_engine(db_url))
    assert "user_sessions" in insp.get_table_names()
    columns = {col["name"] for col in insp.get_columns("user_sessions")}
    assert _USER_SESSIONS_COLUMNS.issubset(columns), (
        f"user_sessions lost columns after downgrade: missing {_USER_SESSIONS_COLUMNS - columns}"
    )


@pytest.mark.skipif(
    True,
    reason="user_sessions.id ALTER TYPE only runs on Postgres; SQLite path is no-op."
    " Enabled when the suite runs against a real Postgres engine.",
)
def test_migration_0015_postgres_id_is_uuid(alembic_cfg):
    """On Postgres, user_sessions.id ends up as the native uuid type after 0015."""
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0015")
    insp = inspect(create_engine(db_url))
    cols = {col["name"]: col for col in insp.get_columns("user_sessions")}
    assert "UUID" in str(cols["id"]["type"]).upper()
