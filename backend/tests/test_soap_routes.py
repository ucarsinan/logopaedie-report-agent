"""Tests for SOAP notes endpoints."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from models.auth import User
from models.report_record import ReportRecord
from models.soap_record import SOAPRecord

_SOAP_PAYLOAD = {
    "subjective": "Patient berichtet über Ausspracheschwierigkeiten.",
    "objective": "Phonologische Prozesse beobachtet: Entstimmlichung.",
    "assessment": "Phonologische Störung, mittlerer Schweregrad.",
    "plan": "Wöchentliche Therapie à 45 Minuten.",
}


@pytest.fixture()
def mock_soap_gen(client):
    """Override get_soap_generator dependency with an AsyncMock."""
    from dependencies import get_soap_generator
    from main import app

    mock_gen = MagicMock()
    mock_gen.generate_from_data = AsyncMock(return_value=_SOAP_PAYLOAD)
    app.dependency_overrides[get_soap_generator] = lambda: mock_gen
    yield mock_gen
    app.dependency_overrides.pop(get_soap_generator, None)


@pytest.fixture()
def report_in_db(test_db, fake_user):
    """Insert a ReportRecord and return its ID."""
    content = {
        "report_type": "befundbericht",
        "patient": {"pseudonym": "T.M.", "age_group": "Kind", "gender": "männlich"},
        "diagnose": {"icd_10_codes": ["F80.0"], "indikationsschluessel": "SP1", "diagnose_text": "Sprachstörung"},
        "befund": "Phonologische Prozesse festgestellt.",
    }
    record = ReportRecord(
        pseudonym="T.M.",
        report_type="befundbericht",
        content_json=json.dumps(content),
        user_id=fake_user.id,
    )
    with Session(test_db) as session:
        session.add(record)
        session.commit()
        session.refresh(record)
        return record.id


class TestGenerateSoapFromSession:
    def test_success(self, client: TestClient, session_id: str, mock_soap_gen):
        resp = client.post(f"/sessions/{session_id}/soap")
        assert resp.status_code == 200
        data = resp.json()
        assert data["subjective"] == _SOAP_PAYLOAD["subjective"]
        assert data["objective"] == _SOAP_PAYLOAD["objective"]
        assert data["assessment"] == _SOAP_PAYLOAD["assessment"]
        assert data["plan"] == _SOAP_PAYLOAD["plan"]
        assert "id" in data
        assert data["session_id"] == session_id

    def test_invalid_session_id_format(self, client: TestClient, mock_soap_gen):
        resp = client.post("/sessions/INVALID/soap")
        assert resp.status_code == 400

    def test_session_not_found(self, client: TestClient, mock_soap_gen):
        resp = client.post("/sessions/aabbccddeeff/soap")
        assert resp.status_code == 404

    def test_persists_record_owned_by_current_user(
        self, client: TestClient, session_id: str, mock_soap_gen, test_db, fake_user
    ):
        """Generated SOAP must be persisted with user_id and session_id set."""
        resp = client.post(f"/sessions/{session_id}/soap")
        assert resp.status_code == 200
        body = resp.json()

        with Session(test_db) as db:
            saved = db.get(SOAPRecord, body["id"])
            assert saved is not None
            assert saved.user_id == fake_user.id
            assert saved.session_id == session_id
            assert saved.report_id is None
            assert saved.subjective == _SOAP_PAYLOAD["subjective"]
            assert saved.plan == _SOAP_PAYLOAD["plan"]

    def test_unauthenticated_returns_401(self, unauth_client):
        resp = unauth_client.post("/sessions/aabbccddeeff/soap")
        assert resp.status_code == 401


class TestGenerateSoapFromReport:
    def test_success(self, client: TestClient, report_in_db: int, mock_soap_gen):
        resp = client.post(f"/reports/{report_in_db}/soap")
        assert resp.status_code == 200
        data = resp.json()
        assert data["report_id"] == report_in_db
        assert "subjective" in data

    def test_report_not_found(self, client: TestClient, mock_soap_gen):
        resp = client.post("/reports/99999/soap")
        assert resp.status_code == 404

    def test_persists_record_linked_to_report(self, client: TestClient, report_in_db: int, mock_soap_gen, test_db):
        resp = client.post(f"/reports/{report_in_db}/soap")
        assert resp.status_code == 200
        body = resp.json()

        with Session(test_db) as db:
            saved = db.get(SOAPRecord, body["id"])
            assert saved is not None
            assert saved.report_id == report_in_db
            assert saved.session_id is None
            assert saved.assessment == _SOAP_PAYLOAD["assessment"]

    def test_unauthenticated_returns_401(self, unauth_client):
        resp = unauth_client.post("/reports/1/soap")
        assert resp.status_code == 401


class TestGetSoapForReport:
    def test_not_found_when_no_soap_generated(self, client: TestClient, report_in_db: int):
        resp = client.get(f"/reports/{report_in_db}/soap")
        assert resp.status_code == 404

    def test_returns_soap_after_generation(self, client: TestClient, report_in_db: int, mock_soap_gen):
        client.post(f"/reports/{report_in_db}/soap")
        resp = client.get(f"/reports/{report_in_db}/soap")
        assert resp.status_code == 200
        data = resp.json()
        assert data["report_id"] == report_in_db

    def test_returns_latest_when_multiple_exist(self, client: TestClient, report_in_db: int, test_db, fake_user):
        """`order_by(created_at DESC).first()` must return the newest record."""
        earlier = datetime.now(UTC) - timedelta(minutes=5)
        with Session(test_db) as db:
            db.add(
                SOAPRecord(
                    report_id=report_in_db,
                    user_id=fake_user.id,
                    subjective="alt-S",
                    objective="alt-O",
                    assessment="alt-A",
                    plan="alt-P",
                    created_at=earlier,
                )
            )
            db.add(
                SOAPRecord(
                    report_id=report_in_db,
                    user_id=fake_user.id,
                    subjective="neu-S",
                    objective="neu-O",
                    assessment="neu-A",
                    plan="neu-P",
                )
            )
            db.commit()

        resp = client.get(f"/reports/{report_in_db}/soap")
        assert resp.status_code == 200
        assert resp.json()["subjective"] == "neu-S"

    def test_returns_404_when_report_does_not_exist(self, client: TestClient):
        resp = client.get("/reports/99999/soap")
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self, unauth_client):
        resp = unauth_client.get("/reports/1/soap")
        assert resp.status_code == 401

    def test_does_not_leak_other_users_soap(self, client: TestClient, test_db):
        """A SOAPRecord owned by a different user must not be returned."""
        other = User(id=uuid4(), email="other@test.example", password_hash="x")
        with Session(test_db) as db:
            db.add(other)
            db.commit()
            db.refresh(other)
            db.add(
                SOAPRecord(
                    report_id=4242,
                    user_id=other.id,
                    subjective="leak-S",
                    objective="leak-O",
                    assessment="leak-A",
                    plan="leak-P",
                )
            )
            db.commit()

        resp = client.get("/reports/4242/soap")
        assert resp.status_code == 404

        with Session(test_db) as db:
            still_there = db.exec(select(SOAPRecord).where(SOAPRecord.report_id == 4242)).first()
            assert still_there is not None  # the record is untouched, just not returned


class TestGetSoapNote:
    def test_get_by_id(self, client: TestClient, test_db, fake_user):
        record = SOAPRecord(
            user_id=fake_user.id,
            subjective="S",
            objective="O",
            assessment="A",
            plan="P",
        )
        with Session(test_db) as session:
            session.add(record)
            session.commit()
            session.refresh(record)
            soap_id = record.id

        resp = client.get(f"/soap/{soap_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["subjective"] == "S"

    def test_not_found(self, client: TestClient):
        resp = client.get("/soap/99999")
        assert resp.status_code == 404


class TestUpdateSoapNote:
    def test_update_success(self, client: TestClient, test_db, fake_user):
        record = SOAPRecord(
            user_id=fake_user.id,
            subjective="Old S",
            objective="Old O",
            assessment="Old A",
            plan="Old P",
        )
        with Session(test_db) as session:
            session.add(record)
            session.commit()
            session.refresh(record)
            soap_id = record.id

        resp = client.put(
            f"/soap/{soap_id}",
            json={"subjective": "New S", "objective": "New O", "assessment": "New A", "plan": "New P"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["subjective"] == "New S"
        assert data["plan"] == "New P"

    def test_update_not_found(self, client: TestClient):
        resp = client.put(
            "/soap/99999",
            json={"subjective": "S", "objective": "O", "assessment": "A", "plan": "P"},
        )
        assert resp.status_code == 404
