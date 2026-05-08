"""Tests for SOAP notes endpoints."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from models.report_record import ReportRecord
from models.soap_record import SOAPRecord


@pytest.fixture()
def mock_soap_gen(client):
    """Override get_soap_generator dependency with an AsyncMock."""
    from dependencies import get_soap_generator
    from main import app

    mock_gen = MagicMock()
    mock_gen.generate_from_data = AsyncMock(
        return_value={
            "subjective": "Patient berichtet über Ausspracheschwierigkeiten.",
            "objective": "Phonologische Prozesse beobachtet: Entstimmlichung.",
            "assessment": "Phonologische Störung, mittlerer Schweregrad.",
            "plan": "Wöchentliche Therapie à 45 Minuten.",
        }
    )
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
        assert data["subjective"] == "Patient berichtet über Ausspracheschwierigkeiten."
        assert data["objective"] == "Phonologische Prozesse beobachtet: Entstimmlichung."
        assert data["assessment"] == "Phonologische Störung, mittlerer Schweregrad."
        assert data["plan"] == "Wöchentliche Therapie à 45 Minuten."
        assert "id" in data
        assert data["session_id"] == session_id

    def test_invalid_session_id_format(self, client: TestClient, mock_soap_gen):
        resp = client.post("/sessions/INVALID/soap")
        assert resp.status_code == 400

    def test_session_not_found(self, client: TestClient, mock_soap_gen):
        resp = client.post("/sessions/aabbccddeeff/soap")
        assert resp.status_code == 404


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
