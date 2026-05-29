"""Migration 0012: align declared FKs across reports, soaprecord, patients,
consent_records, therapyplanrecord.

The 2026-05-29 incident put `therapyplanrecord_user_id_fkey` on Neon by hand;
this migration formalises that as alembic and adds the six other FK constraints
the models declare but the migrations never emitted. The constraint must be a
no-op on environments where the FK already exists (Neon hotfix; fresh dev DB
that was built via create_all).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parent.parent


# (table, constrained_column, referred_table, ondelete) — must match _FK_SPECS in 0012.
_EXPECTED_FKS: list[tuple[str, str, str, str]] = [
    ("reports", "user_id", "users", "CASCADE"),
    ("reports", "patient_id", "patients", "SET NULL"),
    ("soaprecord", "user_id", "users", "CASCADE"),
    ("patients", "user_id", "users", "CASCADE"),
    ("consent_records", "patient_id", "patients", "CASCADE"),
    ("consent_records", "recorded_by", "users", "RESTRICT"),
    ("therapyplanrecord", "user_id", "users", "CASCADE"),
]


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


def _fk_set(insp, table: str) -> set[tuple[str, str, str]]:
    """Return {(constrained_column, referred_table, ondelete)} for table."""
    out: set[tuple[str, str, str]] = set()
    for fk in insp.get_foreign_keys(table):
        cols = fk.get("constrained_columns") or []
        if not cols:
            continue
        ondelete = (fk.get("options") or {}).get("ondelete") or ""
        out.add((cols[0], fk.get("referred_table", ""), ondelete))
    return out


def test_migration_0012_adds_all_declared_fks(alembic_cfg):
    """After upgrade to 0012, all 7 model-declared FKs must be present with
    the correct ondelete behaviour."""
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0011")
    insp = inspect(create_engine(db_url))
    # Before 0012: the named alignment FKs are not present (apart from the
    # inline `therapyplanrecord.report_id -> reports.id` that 0010 created).
    for table, column, referred, _ondelete in _EXPECTED_FKS:
        existing = _fk_set(insp, table)
        assert (column, referred) not in {(c, r) for (c, r, _o) in existing}, (
            f"baseline pre-0012 already has FK {table}.{column}->{referred}; test setup invalid"
        )

    command.upgrade(cfg, "0012")
    insp = inspect(create_engine(db_url))
    for table, column, referred, ondelete in _EXPECTED_FKS:
        existing = _fk_set(insp, table)
        assert (column, referred, ondelete) in existing, (
            f"missing FK {table}.{column} -> {referred}.id ON DELETE {ondelete} (got: {existing})"
        )


def test_migration_0012_is_idempotent_when_fk_preexists(alembic_cfg):
    """Re-running 0012 must be a no-op. Mirrors the Neon-with-hotfix scenario
    for `therapyplanrecord.user_id`: the FK is already there, and the
    `_existing_fks` inspector check must short-circuit instead of erroring."""
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0012")
    insp = inspect(create_engine(db_url))
    fks_after_first = {t: _fk_set(insp, t) for t in {row[0] for row in _EXPECTED_FKS}}

    # Down + up again must end in the same state.
    command.downgrade(cfg, "0011")
    command.upgrade(cfg, "0012")
    insp = inspect(create_engine(db_url))
    fks_after_second = {t: _fk_set(insp, t) for t in {row[0] for row in _EXPECTED_FKS}}

    assert fks_after_second == fks_after_first


def test_migration_0012_downgrade_removes_alignment_fks(alembic_cfg):
    """Downgrade to 0011 removes the 7 alignment FKs but leaves the
    pre-existing inline `therapyplanrecord.report_id -> reports.id` FK alone."""
    cfg, db_url = alembic_cfg
    command.upgrade(cfg, "0012")
    command.downgrade(cfg, "0011")
    insp = inspect(create_engine(db_url))

    for table, column, referred, _ondelete in _EXPECTED_FKS:
        existing = _fk_set(insp, table)
        # The 7 alignment FKs must be gone.
        assert (column, referred) not in {(c, r) for (c, r, _o) in existing}, (
            f"post-downgrade FK {table}.{column}->{referred} should be gone (got: {existing})"
        )

    # The inline report_id -> reports FK created by 0010 must still be there.
    tp_fks = _fk_set(insp, "therapyplanrecord")
    assert any(col == "report_id" and ref == "reports" for (col, ref, _o) in tp_fks), (
        f"expected therapyplanrecord.report_id -> reports.id to survive, got {tp_fks}"
    )
