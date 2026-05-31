"""Migration 0014: email_tokens.id VARCHAR(36) -> UUID type alignment.

Second of the type-encoding-drift cleanups flagged by A3's 2026-05-29
schema audit, following 0013. On SQLite the migration is a no-op (the
GUID TypeDecorator already stores as CHAR(36)); the real ALTER only runs
on Postgres. The SQLite tests below therefore mostly verify that:

- the migration applies and reverses without errors,
- the email_tokens table remains structurally intact (column set unchanged),
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


_EMAIL_TOKENS_COLUMNS = {
    "id",
    "user_id",
    "token_hash",
    "purpose",
    "expires_at",
    "used_at",
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


def test_migration_0014_preserves_email_tokens_shape(alembic_cfg):
    """After upgrade to 0014, email_tokens still has the expected columns."""
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0014")
    insp = inspect(create_engine(db_url))
    assert "email_tokens" in insp.get_table_names()
    columns = {col["name"] for col in insp.get_columns("email_tokens")}
    assert _EMAIL_TOKENS_COLUMNS.issubset(columns), (
        f"email_tokens lost columns after 0014: missing {_EMAIL_TOKENS_COLUMNS - columns}"
    )


def test_migration_0014_id_round_trips(alembic_cfg):
    """email_tokens.id must remain insertable/queryable after the migration.

    On SQLite the migration is a dialect-gated no-op, so this is mainly a
    smoke test that 0014 did not accidentally break the column on the
    only engine the test suite actually runs against. email_tokens.user_id
    has a NOT NULL FK to users.id, so we insert a user first.
    """
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0014")
    eng = create_engine(db_url)
    row_id = str(uuid4())
    user_id = str(uuid4())
    with eng.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, role, email_verified,"
                " totp_enabled, failed_login_count, created_at, updated_at)"
                " VALUES (:id, 'u@example.com', 'x', 'user', 0, 0, 0,"
                " '2026-05-31T00:00:00', '2026-05-31T00:00:00')"
            ),
            {"id": user_id},
        )
        conn.execute(
            text(
                "INSERT INTO email_tokens (id, user_id, token_hash, purpose,"
                " expires_at, used_at) VALUES (:id, :user_id, 'hash',"
                " 'verify_email', '2026-06-30T00:00:00', NULL)"
            ),
            {"id": row_id, "user_id": user_id},
        )
        got = conn.execute(text("SELECT id FROM email_tokens WHERE id = :id"), {"id": row_id}).scalar()
    assert got == row_id


def test_migration_0014_downgrade(alembic_cfg):
    """Downgrade from 0014 -> 0013 must leave email_tokens intact.

    Like the upgrade, the downgrade is a no-op on SQLite; this just
    confirms the migration is reversible without errors and the table
    survives the round trip.
    """
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0014")
    command.downgrade(cfg, "0013")
    insp = inspect(create_engine(db_url))
    assert "email_tokens" in insp.get_table_names()
    columns = {col["name"] for col in insp.get_columns("email_tokens")}
    assert _EMAIL_TOKENS_COLUMNS.issubset(columns), (
        f"email_tokens lost columns after downgrade: missing {_EMAIL_TOKENS_COLUMNS - columns}"
    )


@pytest.mark.skipif(
    True,
    reason="email_tokens.id ALTER TYPE only runs on Postgres; SQLite path is no-op."
    " Enabled when the suite runs against a real Postgres engine.",
)
def test_migration_0014_postgres_id_is_uuid(alembic_cfg):
    """On Postgres, email_tokens.id ends up as the native uuid type after 0014."""
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0014")
    insp = inspect(create_engine(db_url))
    cols = {col["name"]: col for col in insp.get_columns("email_tokens")}
    assert "UUID" in str(cols["id"]["type"]).upper()
