"""Tests for ReportRecord persistence layer."""
from __future__ import annotations

import json
import sys
import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # share a single in-memory connection across sessions
)

from backend.models.report_record import ReportRecord  # noqa: E402 — must be imported before create_all

# Pre-register short-name aliases so that main.py's sys.path-based imports (`from models.X import …`)
# resolve to the SAME module objects as `backend.models.X` — prevents duplicate SQLModel registrations.
for _key in list(sys.modules):
    if _key.startswith("backend."):
        _short = _key[len("backend."):]
        if _short not in sys.modules:
            sys.modules[_short] = sys.modules[_key]


@pytest.fixture(autouse=True)
def setup_tables():
    SQLModel.metadata.create_all(test_engine, checkfirst=True)
    yield
    SQLModel.metadata.drop_all(test_engine)


def test_report_record_can_be_created():

    with Session(test_engine) as db:
        record = ReportRecord(
            pseudonym="Max M.",
            report_type="befundbericht",
            content_json=json.dumps({"report_type": "befundbericht", "patient": {"pseudonym": "Max M."}}),
        )
        db.add(record)
        db.commit()
        db.refresh(record)

    assert record.id is not None
    assert record.pseudonym == "Max M."
    assert record.report_type == "befundbericht"
    assert record.created_at is not None


def test_generate_endpoint_saves_report_to_db(mock_groq):
    import json
    import sys
    from fastapi.testclient import TestClient
    from unittest.mock import AsyncMock, MagicMock, patch
    from backend.main import app
    # main.py loads `database` via sys.path, not `backend.database`.
    # We must override using the same function object that FastAPI registered.
    database_mod = sys.modules.get("database") or sys.modules["backend.database"]
    get_db = database_mod.get_db
    from sqlmodel import Session, select
    from backend.models.report_record import ReportRecord

    def override_get_db():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    fake_report = {
        "report_type": "befundbericht",
        "patient": {"pseudonym": "Anna B.", "age_group": "kind", "gender": None},
        "diagnose": {"icd_10_codes": [], "indikationsschluessel": "", "diagnose_text": ""},
        "anamnese": "Test", "befund": "", "therapieindikation": "",
        "therapieziele": [], "empfehlung": "",
    }

    with patch("services.report_generator.ReportGenerator.generate", new_callable=AsyncMock) as mock_gen:
        mock_report_obj = MagicMock()
        mock_report_obj.model_dump.return_value = fake_report
        mock_gen.return_value = mock_report_obj
        mock_groq["chat"].return_value = "Willkommen!"

        client = TestClient(app)
        res = client.post("/sessions")
        assert res.status_code == 200
        session_id = res.json()["session_id"]

        from backend.services.session_store import store
        session = store.get(session_id)
        session.status = "materials"
        store.save(session)

        res = client.post(f"/sessions/{session_id}/generate")
        assert res.status_code == 200

    with Session(test_engine) as db:
        records = db.exec(select(ReportRecord)).all()

    assert len(records) == 1
    assert records[0].pseudonym == "Anna B."
    assert records[0].report_type == "befundbericht"

    app.dependency_overrides.clear()


def test_list_reports_returns_saved_records():
    import sys
    from fastapi.testclient import TestClient
    from backend.main import app
    from sqlmodel import Session
    from backend.models.report_record import ReportRecord

    database_mod = sys.modules.get("database") or sys.modules["backend.database"]
    get_db = database_mod.get_db

    def override_get_db():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    with Session(test_engine) as db:
        db.add(ReportRecord(pseudonym="A", report_type="befundbericht", content_json="{}"))
        db.add(ReportRecord(pseudonym="B", report_type="abschlussbericht", content_json="{}"))
        db.commit()

    client = TestClient(app)
    res = client.get("/reports")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    assert {r["pseudonym"] for r in data} == {"A", "B"}
    assert "id" in data[0]
    assert "created_at" in data[0]

    app.dependency_overrides.clear()


def test_get_single_report_returns_full_content():
    import json
    import sys
    from fastapi.testclient import TestClient
    from backend.main import app
    from sqlmodel import Session
    from backend.models.report_record import ReportRecord

    database_mod = sys.modules.get("database") or sys.modules["backend.database"]
    get_db = database_mod.get_db

    def override_get_db():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    content = {"report_type": "befundbericht", "patient": {"pseudonym": "X"}}
    with Session(test_engine) as db:
        record = ReportRecord(pseudonym="X", report_type="befundbericht", content_json=json.dumps(content))
        db.add(record)
        db.commit()
        db.refresh(record)
        record_id = record.id

    client = TestClient(app)
    res = client.get(f"/reports/{record_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["report_type"] == "befundbericht"
    assert data["_db_id"] == record_id
    assert "created_at" in data

    app.dependency_overrides.clear()


def test_get_nonexistent_report_returns_404():
    import sys
    from fastapi.testclient import TestClient
    from backend.main import app
    from sqlmodel import Session

    database_mod = sys.modules.get("database") or sys.modules["backend.database"]
    get_db = database_mod.get_db

    def override_get_db():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    res = client.get("/reports/99999")
    assert res.status_code == 404

    app.dependency_overrides.clear()
