"""Additional tests for /reports endpoints: stats, filters."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from models.auth import User
from models.report_record import ReportRecord

TEST_USER_ID = uuid4()


@pytest.fixture
def reports_client(monkeypatch):
    """Client with in-memory DB, pre-created fake user."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("KV_REST_API_URL", "https://fake-redis.test")
    monkeypatch.setenv("KV_REST_API_TOKEN", "fake-token")
    monkeypatch.delenv("SERVICE_TOKEN", raising=False)
    from cryptography.fernet import Fernet

    monkeypatch.setenv("PATIENT_ENCRYPTION_KEY", Fernet.generate_key().decode())

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    import models.soap_record
    import models.therapy_plan_record  # noqa: F401

    SQLModel.metadata.create_all(engine)

    fake_user = User(id=TEST_USER_ID, email="stats@test.example", password_hash="x")
    with Session(engine) as db:
        db.add(fake_user)
        db.commit()

    from database import get_db
    from dependencies import get_current_user
    from main import app

    def _db_override():
        with Session(engine) as db:
            yield db

    # Use a plain lambda that returns a detached-safe user object
    _user = User(id=TEST_USER_ID, email="stats@test.example", password_hash="x")
    app.dependency_overrides[get_current_user] = lambda: _user
    app.dependency_overrides[get_db] = _db_override

    client = TestClient(app)
    client._engine = engine  # type: ignore[attr-defined]
    yield client

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


def _insert_records(engine, records):
    with Session(engine) as db:
        for r in records:
            db.add(r)
        db.commit()


class TestReportStats:
    def test_stats_empty(self, reports_client):
        res = reports_client.get("/reports/stats")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 0
        assert data["by_type"] == {}
        assert data["latest_date"] is None

    def test_stats_with_records(self, reports_client):
        _insert_records(
            reports_client._engine,
            [
                ReportRecord(
                    pseudonym="A",
                    report_type="befundbericht",
                    content_json="{}",
                    user_id=TEST_USER_ID,
                ),
                ReportRecord(
                    pseudonym="B",
                    report_type="befundbericht",
                    content_json="{}",
                    user_id=TEST_USER_ID,
                ),
                ReportRecord(
                    pseudonym="C",
                    report_type="abschlussbericht",
                    content_json="{}",
                    user_id=TEST_USER_ID,
                ),
            ],
        )
        res = reports_client.get("/reports/stats")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 3
        assert data["by_type"]["befundbericht"] == 2
        assert data["by_type"]["abschlussbericht"] == 1
        assert data["latest_date"] is not None


class TestReportFilters:
    def test_filter_by_pseudonym(self, reports_client):
        _insert_records(
            reports_client._engine,
            [
                ReportRecord(
                    pseudonym="Anna Muster",
                    report_type="befundbericht",
                    content_json="{}",
                    user_id=TEST_USER_ID,
                ),
                ReportRecord(
                    pseudonym="Klaus Beispiel",
                    report_type="befundbericht",
                    content_json="{}",
                    user_id=TEST_USER_ID,
                ),
            ],
        )
        res = reports_client.get("/reports?pseudonym=anna")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["pseudonym"] == "Anna Muster"

    def test_filter_by_report_type(self, reports_client):
        _insert_records(
            reports_client._engine,
            [
                ReportRecord(
                    pseudonym="P1",
                    report_type="befundbericht",
                    content_json="{}",
                    user_id=TEST_USER_ID,
                ),
                ReportRecord(
                    pseudonym="P2",
                    report_type="abschlussbericht",
                    content_json="{}",
                    user_id=TEST_USER_ID,
                ),
            ],
        )
        res = reports_client.get("/reports?report_type=abschlussbericht")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["report_type"] == "abschlussbericht"

    def test_filter_by_from_date(self, reports_client):
        _insert_records(
            reports_client._engine,
            [
                ReportRecord(
                    pseudonym="P",
                    report_type="befundbericht",
                    content_json="{}",
                    user_id=TEST_USER_ID,
                ),
            ],
        )
        # Future date → should return 0 results
        res = reports_client.get("/reports?from_date=2099-01-01T00:00:00")
        assert res.status_code == 200
        assert res.json()["total"] == 0

    def test_filter_by_to_date(self, reports_client):
        _insert_records(
            reports_client._engine,
            [
                ReportRecord(
                    pseudonym="P",
                    report_type="befundbericht",
                    content_json="{}",
                    user_id=TEST_USER_ID,
                ),
            ],
        )
        # Past date → should return 0 results
        res = reports_client.get("/reports?to_date=2000-01-01T00:00:00")
        assert res.status_code == 200
        assert res.json()["total"] == 0

    def test_filter_invalid_date_ignored(self, reports_client):
        """Invalid date strings should be silently ignored (no 500)."""
        res = reports_client.get("/reports?from_date=not-a-date&to_date=also-not-a-date")
        assert res.status_code == 200

    def test_pagination(self, reports_client):
        _insert_records(
            reports_client._engine,
            [
                ReportRecord(
                    pseudonym=f"P{i}",
                    report_type="befundbericht",
                    content_json="{}",
                    user_id=TEST_USER_ID,
                )
                for i in range(5)
            ],
        )
        res = reports_client.get("/reports?page=1&limit=2")
        assert res.status_code == 200
        data = res.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
