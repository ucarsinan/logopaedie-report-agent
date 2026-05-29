"""Migration 0006: SOAP ownership."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parent.parent


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


def test_migration_0006_creates_owned_soap_table_on_fresh_db(alembic_cfg):
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0006")
    insp = inspect(create_engine(db_url))
    columns = {col["name"]: col for col in insp.get_columns("soaprecord")}
    assert "user_id" in columns
    assert columns["user_id"]["nullable"] is False
    indexes = {idx["name"] for idx in insp.get_indexes("soaprecord")}
    assert "ix_soaprecord_user_id" in indexes


def test_migration_0006_backfills_report_owned_soap_and_drops_orphans(alembic_cfg):
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0005")
    eng = create_engine(db_url)
    with eng.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE soaprecord (
                    id INTEGER PRIMARY KEY,
                    report_id INTEGER,
                    session_id VARCHAR,
                    subjective VARCHAR NOT NULL,
                    objective VARCHAR NOT NULL,
                    assessment VARCHAR NOT NULL,
                    plan VARCHAR NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, role, email_verified, created_at, updated_at)"
                " VALUES ('00000000-0000-0000-0000-000000000001', 'a@test.example', 'x', 'user', 1,"
                " '2026-01-01T00:00:00', '2026-01-01T00:00:00')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO reports (id, pseudonym, report_type, created_at, content_json, user_id)"
                " VALUES (1, 'P', 'befundbericht', '2026-01-01T00:00:00', '{}',"
                " '00000000-0000-0000-0000-000000000001')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO soaprecord (id, report_id, session_id, subjective, objective, assessment, plan, created_at)"
                " VALUES (1, 1, NULL, 'S', 'O', 'A', 'P', '2026-01-01T00:00:00')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO soaprecord (id, report_id, session_id, subjective, objective, assessment, plan, created_at)"
                " VALUES (2, NULL, 'abcdef123456', 'S', 'O', 'A', 'P', '2026-01-01T00:00:00')"
            )
        )

    command.upgrade(cfg, "0006")

    with eng.begin() as conn:
        rows = conn.execute(text("SELECT id, user_id FROM soaprecord ORDER BY id")).all()
    assert rows == [(1, "00000000-0000-0000-0000-000000000001")]
