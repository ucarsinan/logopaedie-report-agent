"""Migration 0005: reports.user_id — shape + data-drop tests."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

from alembic import command
from alembic.config import Config

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture
def alembic_cfg():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_name = tmp.name
    url = f"sqlite:///{tmp_name}"
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    yield cfg, url
    os.unlink(tmp_name)


def test_migration_0005_drops_existing_reports(alembic_cfg):
    """Existing orphaned reports must be deleted during upgrade."""
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0004")
    eng = create_engine(db_url)
    with eng.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO reports (id, pseudonym, report_type, content_json, created_at)"
                " VALUES (1, 'x', 'befundbericht', '{}', '2026-01-01T00:00:00')"
            )
        )
    command.upgrade(cfg, "0005")
    with eng.begin() as conn:
        rows = conn.execute(text("SELECT COUNT(*) FROM reports")).scalar()
    assert rows == 0


def test_migration_0005_user_id_column_shape(alembic_cfg):
    """After upgrade, reports must have a NOT NULL user_id column and index."""
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0005")
    insp = inspect(create_engine(db_url))
    columns = {col["name"]: col for col in insp.get_columns("reports")}
    assert "user_id" in columns
    assert columns["user_id"]["nullable"] is False
    indexes = {idx["name"] for idx in insp.get_indexes("reports")}
    assert "ix_reports_user_id" in indexes


def test_migration_0005_downgrade(alembic_cfg):
    """Downgrade to 0004 removes user_id column from reports."""
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0005")
    command.downgrade(cfg, "0004")
    insp = inspect(create_engine(db_url))
    columns = {col["name"] for col in insp.get_columns("reports")}
    assert "user_id" not in columns
