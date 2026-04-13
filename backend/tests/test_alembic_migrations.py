"""Alembic upgrade/downgrade smoke tests."""

import os
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

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


def test_alembic_upgrade_baseline(alembic_cfg):
    cfg, url = alembic_cfg
    command.upgrade(cfg, "0001")
    insp = inspect(create_engine(url))
    assert "reports" in insp.get_table_names()
    columns = {col["name"] for col in insp.get_columns("reports")}
    assert columns == {"id", "pseudonym", "report_type", "created_at", "content_json"}
    indexes = {idx["name"] for idx in insp.get_indexes("reports")}
    assert "ix_reports_pseudonym" in indexes


def test_alembic_downgrade_baseline(alembic_cfg):
    cfg, url = alembic_cfg
    command.upgrade(cfg, "0001")
    command.downgrade(cfg, "base")
    insp = inspect(create_engine(url))
    assert "reports" not in insp.get_table_names()


def test_alembic_upgrade_head_fresh_db(alembic_cfg):
    cfg, url = alembic_cfg
    command.upgrade(cfg, "head")
    insp = inspect(create_engine(url))
    tables = set(insp.get_table_names())
    assert {"reports", "users", "user_sessions", "email_tokens", "audit_log"} <= tables
    user_indexes = {ix["name"] for ix in insp.get_indexes("users")}
    sess_indexes = {ix["name"] for ix in insp.get_indexes("user_sessions")}
    assert "ix_users_email" in user_indexes
    assert "ix_user_sessions_refresh_token_hash" in sess_indexes


def test_alembic_downgrade_0002(alembic_cfg):
    cfg, url = alembic_cfg
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0001")
    insp = inspect(create_engine(url))
    tables = set(insp.get_table_names())
    assert "users" not in tables
    assert "user_sessions" not in tables
    assert "email_tokens" not in tables
    assert "audit_log" not in tables
    assert "reports" in tables
