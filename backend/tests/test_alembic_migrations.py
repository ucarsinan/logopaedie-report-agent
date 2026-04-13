"""Alembic upgrade/downgrade smoke tests."""

import os
import tempfile
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command

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
