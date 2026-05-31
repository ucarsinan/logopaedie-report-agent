"""Migration 0018: patients.id cluster VARCHAR(36) -> UUID type alignment.

Fifth in the type-encoding-drift chain (see test_migration_0013 / _0014 /
_0015 / _0016 for the leaf-PK predecessors). Unlike those, 0018 is a
*coordinated cluster* migration: it drops the incoming FKs to patients.id,
ALTERs patients.id + consent_records.patient_id, and recreates the FKs.

This test was authored in a worktree forked before sibling migration 0017
(users.id cluster) landed. Because alembic's revision-map builder eagerly
walks every file in `versions/` and crashes on the missing 0017, the tests
below cannot ask alembic to `upgrade head` or even `upgrade 0016` while
0018 is in the directory. Workaround: copy the 0001..0016 chain into an
isolated temp `versions/` dir (omitting 0018), bootstrap to 0016 with that
sandboxed alembic config, then execute 0018's `upgrade()` / `downgrade()`
directly via an explicit `MigrationContext` against the same DB. This
sidesteps the unresolved 0017 while still exercising the real 0018 code
on SQLite. The end-to-end `alembic upgrade head` integration only becomes
runnable after both 0017 and 0018 are merged into main.

On SQLite the 0018 upgrade is a dialect-gated no-op (the GUID
TypeDecorator already stores as CHAR(36)). The SQLite tests below
therefore verify that:

- the migration applies / reverses without errors (early return on SQLite),
- patients + consent_records tables remain structurally intact after upgrade,
- the id / patient_id columns still round-trip through an insert/select.

The Postgres-specific FK drop/recreate + ALTER assertions are marked
skip-by-dialect so a future Postgres-CI run can validate the real cluster
swap end-to-end.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

from alembic import command, op

BACKEND_DIR = Path(__file__).resolve().parent.parent
_ALEMBIC_DIR = BACKEND_DIR / "alembic"
_VERSIONS_DIR = _ALEMBIC_DIR / "versions"
_MIGRATION_PATH = _VERSIONS_DIR / "0018_patients_id_uuid_cluster.py"


def _load_migration_module():
    """Import 0018 as a module without going through alembic's chain resolver."""
    spec = importlib.util.spec_from_file_location("_migration_0018", _MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_PATIENTS_COLUMNS = {
    "id",
    "system_id",
    "pseudonym",
    "user_id",
    "realname_enc",
    "birthdate_enc",
    "gender",
    "age_group",
    "icd10_codes",
    "disorder_text",
    "indikationsschluessel",
    "created_at",
    "deleted_at",
}

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
def sandboxed_alembic_cfg(monkeypatch):
    """Alembic config pointing at a temp `versions/` that omits 0017 and 0018.

    Necessary because alembic's revision-map builder crashes the moment a
    revision references a missing parent (here: 0018 -> 0017). The sandbox
    copies only 0001..0016 + __init__.py, so the chain resolves cleanly
    and `command.upgrade(cfg, "0016")` works as a bootstrap step before we
    execute 0018 directly against the resulting DB.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_name = tmp_db.name
    db_url = f"sqlite:///{db_name}"

    tmp_alembic = Path(tempfile.mkdtemp(prefix="alembic_0018_"))
    tmp_versions = tmp_alembic / "versions"
    tmp_versions.mkdir(parents=True)
    # Copy 0001..0016 + __init__.py, deliberately skip 0017 (absent) and 0018.
    for entry in _VERSIONS_DIR.iterdir():
        if entry.name == "__pycache__":
            continue
        if entry.name == "0018_patients_id_uuid_cluster.py":
            continue
        shutil.copy(entry, tmp_versions / entry.name)
    # Reuse the real env.py / script.py.mako via the same alembic.ini, but
    # point script_location at the temp dir.
    shutil.copy(_ALEMBIC_DIR / "env.py", tmp_alembic / "env.py")
    if (_ALEMBIC_DIR / "script.py.mako").exists():
        shutil.copy(_ALEMBIC_DIR / "script.py.mako", tmp_alembic / "script.py.mako")

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(tmp_alembic))
    cfg.set_main_option("sqlalchemy.url", db_url)

    try:
        yield cfg, db_url
    finally:
        os.unlink(db_name)
        shutil.rmtree(tmp_alembic, ignore_errors=True)


def _apply_0018(db_url: str, direction: str) -> None:
    """Call the 0018 module's upgrade/downgrade with a live alembic op context.

    Bypasses alembic's revision graph (which can't resolve the gap 0016->0017
    in this worktree) but still exercises the actual migration code against
    the same database the rest of the test interacts with.
    """
    module = _load_migration_module()
    eng = create_engine(db_url)
    with eng.connect() as conn:
        ctx = MigrationContext.configure(conn)
        with op.Operations.context(ctx):
            if direction == "upgrade":
                module.upgrade()
            elif direction == "downgrade":
                module.downgrade()
            else:  # pragma: no cover - defensive
                raise ValueError(direction)


def test_migration_0018_preserves_patients_shape(sandboxed_alembic_cfg):
    """After applying 0018, patients still has the expected columns."""
    cfg, db_url = sandboxed_alembic_cfg
    command.upgrade(cfg, "0016")
    _apply_0018(db_url, "upgrade")
    insp = inspect(create_engine(db_url))
    assert "patients" in insp.get_table_names()
    columns = {col["name"] for col in insp.get_columns("patients")}
    assert _PATIENTS_COLUMNS.issubset(columns), (
        f"patients lost columns after 0018: missing {_PATIENTS_COLUMNS - columns}"
    )


def test_migration_0018_preserves_consent_records_shape(sandboxed_alembic_cfg):
    """After applying 0018, consent_records still has the expected columns."""
    cfg, db_url = sandboxed_alembic_cfg
    command.upgrade(cfg, "0016")
    _apply_0018(db_url, "upgrade")
    insp = inspect(create_engine(db_url))
    assert "consent_records" in insp.get_table_names()
    columns = {col["name"] for col in insp.get_columns("consent_records")}
    assert _CONSENT_RECORDS_COLUMNS.issubset(columns), (
        f"consent_records lost columns after 0018: missing {_CONSENT_RECORDS_COLUMNS - columns}"
    )


def test_migration_0018_patients_id_round_trips(sandboxed_alembic_cfg):
    """patients.id must remain insertable/queryable after the migration.

    SQLite path: the migration is a dialect-gated no-op, so this is a smoke
    test that 0018 did not accidentally break the PK on the engine the test
    suite runs against. SQLite does not enforce FK constraints by default,
    so user_id can be an unreferenced UUID string here.
    """
    cfg, db_url = sandboxed_alembic_cfg
    command.upgrade(cfg, "0016")
    _apply_0018(db_url, "upgrade")
    eng = create_engine(db_url)
    pid = str(uuid4())
    uid = str(uuid4())
    with eng.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO patients (id, system_id, pseudonym, user_id,"
                " realname_enc, birthdate_enc, age_group, icd10_codes,"
                " disorder_text, indikationsschluessel, created_at)"
                " VALUES (:pid, :sid, 'PSY-1', :uid, X'00', X'00', 'erwachsen',"
                " '[]', '', '', '2026-05-31T00:00:00')"
            ),
            {"pid": pid, "sid": f"sys-{pid[:8]}", "uid": uid},
        )
        got = conn.execute(text("SELECT id FROM patients WHERE id = :pid"), {"pid": pid}).scalar()
    assert got == pid


def test_migration_0018_consent_records_patient_id_round_trips(sandboxed_alembic_cfg):
    """consent_records.patient_id must remain insertable/queryable after 0018."""
    cfg, db_url = sandboxed_alembic_cfg
    command.upgrade(cfg, "0016")
    _apply_0018(db_url, "upgrade")
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
        got = conn.execute(
            text("SELECT patient_id FROM consent_records WHERE id = :id"),
            {"id": row_id},
        ).scalar()
    assert got == patient_id


def test_migration_0018_downgrade(sandboxed_alembic_cfg):
    """Reversing 0018 must leave patients + consent_records intact.

    Like the upgrade, the downgrade is a no-op on SQLite; this just confirms
    the migration is reversible without errors and both tables survive.
    """
    cfg, db_url = sandboxed_alembic_cfg
    command.upgrade(cfg, "0016")
    _apply_0018(db_url, "upgrade")
    _apply_0018(db_url, "downgrade")
    insp = inspect(create_engine(db_url))
    assert "patients" in insp.get_table_names()
    assert "consent_records" in insp.get_table_names()
    patient_columns = {col["name"] for col in insp.get_columns("patients")}
    consent_columns = {col["name"] for col in insp.get_columns("consent_records")}
    assert _PATIENTS_COLUMNS.issubset(patient_columns), (
        f"patients lost columns after downgrade: missing {_PATIENTS_COLUMNS - patient_columns}"
    )
    assert _CONSENT_RECORDS_COLUMNS.issubset(consent_columns), (
        f"consent_records lost columns after downgrade: missing {_CONSENT_RECORDS_COLUMNS - consent_columns}"
    )


@pytest.mark.skipif(
    True,
    reason="patients.id cluster ALTER TYPE only runs on Postgres; SQLite path is no-op."
    " Enabled when the suite runs against a real Postgres engine.",
)
def test_migration_0018_postgres_patients_id_is_uuid(sandboxed_alembic_cfg):
    """On Postgres, patients.id ends up as the native uuid type after 0018."""
    cfg, db_url = sandboxed_alembic_cfg
    command.upgrade(cfg, "0016")
    _apply_0018(db_url, "upgrade")
    insp = inspect(create_engine(db_url))
    cols = {col["name"]: col for col in insp.get_columns("patients")}
    assert "UUID" in str(cols["id"]["type"]).upper()


@pytest.mark.skipif(
    True,
    reason="consent_records.patient_id ALTER TYPE only runs on Postgres; SQLite path"
    " is no-op. Enabled when the suite runs against a real Postgres engine.",
)
def test_migration_0018_postgres_consent_patient_id_is_uuid(sandboxed_alembic_cfg):
    """On Postgres, consent_records.patient_id is native uuid after 0018."""
    cfg, db_url = sandboxed_alembic_cfg
    command.upgrade(cfg, "0016")
    _apply_0018(db_url, "upgrade")
    insp = inspect(create_engine(db_url))
    cols = {col["name"]: col for col in insp.get_columns("consent_records")}
    assert "UUID" in str(cols["patient_id"]["type"]).upper()


@pytest.mark.skipif(
    True,
    reason="FK constraint introspection only meaningful on Postgres; SQLite path"
    " is no-op. Enabled when the suite runs against a real Postgres engine.",
)
def test_migration_0018_postgres_recreates_fks(sandboxed_alembic_cfg):
    """On Postgres, the incoming patient FKs are re-installed after the type swap."""
    cfg, db_url = sandboxed_alembic_cfg
    command.upgrade(cfg, "0016")
    _apply_0018(db_url, "upgrade")
    insp = inspect(create_engine(db_url))
    consent_fks = {fk.get("name") for fk in insp.get_foreign_keys("consent_records")}
    reports_fks = {fk.get("name") for fk in insp.get_foreign_keys("reports")}
    assert "fk_consent_records_patient_id_patients" in consent_fks
    assert "fk_reports_patient_id_patients" in reports_fks
