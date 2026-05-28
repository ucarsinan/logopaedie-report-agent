"""Tests for therapy plan endpoints (POST session-scoped, save/list/get/update)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock
from uuid import uuid4

from sqlmodel import Session

from models.auth import User
from models.therapy_plan_record import TherapyPlanRecord

_PLAN_DATA = {
    "patient_pseudonym": "K.M.",
    "diagnose_text": "Phonologische Störung",
    "plan_phases": [
        {
            "phase_name": "Phase 1",
            "duration": "8 Sitzungen",
            "goals": [
                {
                    "icf_code": "b320",
                    "goal_text": "Velarlaute stabilisieren",
                    "methods": ["POPT"],
                    "milestones": ["Lautebene"],
                    "timeframe": "Sitzung 1-8",
                }
            ],
        }
    ],
    "frequency": "2x/Woche",
    "total_sessions": 10,
    "elternberatung": "Tägliches Üben empfohlen.",
    "haeusliche_uebungen": ["Bildkarten"],
}


_FULL_PLAN_PAYLOAD = {
    "patient_pseudonym": "L.K.",
    "diagnose_text": "Sprachentwicklungsstörung (F80.0)",
    "plan_phases": [
        {
            "phase_name": "Aufbauphase",
            "duration": "10 Sitzungen",
            "goals": [
                {
                    "icf_code": "b320",
                    "goal_text": "Korrekte Produktion von /k/ und /g/ im Anlaut.",
                    "methods": ["P.O.P.T."],
                    "milestones": ["Lautanbahnung", "Wortebene"],
                    "timeframe": "Sitzung 1-10",
                }
            ],
        },
        {
            "phase_name": "Transferphase",
            "duration": "10 Sitzungen",
            "goals": [
                {
                    "icf_code": "b330",
                    "goal_text": "Transfer in die Spontansprache.",
                    "methods": ["Spielsequenzen", "Geschichten erzählen"],
                    "milestones": ["Satzebene", "Spontansprache"],
                    "timeframe": "Sitzung 11-20",
                }
            ],
        },
    ],
    "frequency": "2x pro Woche, 45 Min.",
    "total_sessions": 20,
    "elternberatung": "Korrektives Feedback im Alltag einsetzen.",
    "haeusliche_uebungen": ["Minimalpaare üben", "Bildkarten benennen"],
}


# ── POST /sessions/{id}/therapy-plan ──────────────────────────────────────────


class TestGenerateTherapyPlanFromSession:
    def test_generate_returns_multi_phase_shape(self, client, session_id, mock_groq):
        """Happy path with two phases — asserts the full TherapyPlan contract."""
        mock_groq["json"].return_value = _FULL_PLAN_PAYLOAD

        res = client.post(f"/sessions/{session_id}/therapy-plan")

        assert res.status_code == 200
        data = res.json()
        assert data["patient_pseudonym"] == "L.K."
        assert data["frequency"] == "2x pro Woche, 45 Min."
        assert data["total_sessions"] == 20
        assert len(data["plan_phases"]) == 2
        phase_names = [p["phase_name"] for p in data["plan_phases"]]
        assert phase_names == ["Aufbauphase", "Transferphase"]
        assert data["plan_phases"][1]["goals"][0]["icf_code"] == "b330"
        assert data["haeusliche_uebungen"] == ["Minimalpaare üben", "Bildkarten benennen"]

    def test_generate_invalid_session_id_returns_400(self, client):
        """Session-id regex (`^[0-9a-f]{12}$`) rejects non-hex / wrong length."""
        res = client.post("/sessions/NOT-A-HEX-ID/therapy-plan")
        assert res.status_code == 400

    def test_generate_unauthenticated_returns_401(self, unauth_client):
        res = unauth_client.post("/sessions/aabbccddeeff/therapy-plan")
        assert res.status_code == 401

    def test_generate_passes_session_to_planner(self, client, session_id, mock_groq, monkeypatch):
        """The router must call therapy_planner.generate_plan with the live session."""
        from dependencies import therapy_planner
        from models.schemas import TherapyPlan

        fake = AsyncMock(return_value=TherapyPlan(**_FULL_PLAN_PAYLOAD))
        monkeypatch.setattr(therapy_planner, "generate_plan", fake)

        res = client.post(f"/sessions/{session_id}/therapy-plan")

        assert res.status_code == 200
        fake.assert_awaited_once()
        passed_session = fake.await_args.args[0]
        assert passed_session.session_id == session_id


# ── POST /therapy-plans (save with explicit plan_data) ────────────────────────


class TestSaveTherapyPlan:
    def test_save_with_plan_data(self, client, session_id):
        res = client.post(
            "/therapy-plans",
            json={"session_id": session_id, "plan_data": _PLAN_DATA},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["patient_pseudonym"] == "K.M."
        assert "id" in data
        assert "created_at" in data

    def test_save_generates_plan_when_no_plan_data(self, client, session_id, mock_groq):
        mock_groq["json"].return_value = _PLAN_DATA
        res = client.post(
            "/therapy-plans",
            json={"session_id": session_id},
        )
        assert res.status_code == 201
        data = res.json()
        assert "id" in data

    def test_save_session_not_found(self, client):
        res = client.post(
            "/therapy-plans",
            json={"session_id": "aabbccddeeff", "plan_data": _PLAN_DATA},
        )
        assert res.status_code == 404

    def test_save_invalid_session_id(self, client):
        res = client.post(
            "/therapy-plans",
            json={"session_id": "INVALID_ID", "plan_data": _PLAN_DATA},
        )
        assert res.status_code == 400

    def test_save_with_report_id(self, client, session_id, test_db, fake_user):
        from models.report_record import ReportRecord

        with Session(test_db) as db:
            record = ReportRecord(
                pseudonym="K.M.",
                report_type="befundbericht",
                content_json="{}",
                user_id=fake_user.id,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            report_id = record.id

        res = client.post(
            "/therapy-plans",
            json={"session_id": session_id, "plan_data": _PLAN_DATA, "report_id": report_id},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["report_id"] == report_id


# ── GET /therapy-plans ────────────────────────────────────────────────────────


class TestListTherapyPlans:
    def test_list_empty(self, client):
        res = client.get("/therapy-plans")
        assert res.status_code == 200
        assert res.json() == []

    def test_list_returns_saved_plans(self, client, test_db, fake_user):
        with Session(test_db) as db:
            db.add(
                TherapyPlanRecord(
                    patient_pseudonym="A.B.",
                    plan_data=json.dumps({"patient_pseudonym": "A.B."}),
                    user_id=fake_user.id,
                )
            )
            db.add(
                TherapyPlanRecord(
                    patient_pseudonym="C.D.",
                    plan_data=json.dumps({"patient_pseudonym": "C.D."}),
                    user_id=fake_user.id,
                )
            )
            db.commit()

        res = client.get("/therapy-plans")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2
        pseudonyms = {item["patient_pseudonym"] for item in data}
        assert "A.B." in pseudonyms
        assert "C.D." in pseudonyms

    def test_list_does_not_leak_other_users_plans(self, client, test_db, fake_user):
        """A TherapyPlanRecord owned by a different user must not appear in the list."""
        other = User(id=uuid4(), email="other@test.example", password_hash="x")
        with Session(test_db) as db:
            db.add(other)
            db.commit()
            db.refresh(other)
            db.add(
                TherapyPlanRecord(
                    patient_pseudonym="Mine",
                    plan_data=json.dumps({"patient_pseudonym": "Mine"}),
                    user_id=fake_user.id,
                )
            )
            db.add(
                TherapyPlanRecord(
                    patient_pseudonym="Theirs",
                    plan_data=json.dumps({"patient_pseudonym": "Theirs"}),
                    user_id=other.id,
                )
            )
            db.commit()

        res = client.get("/therapy-plans")
        assert res.status_code == 200
        data = res.json()
        pseudonyms = {item["patient_pseudonym"] for item in data}
        assert pseudonyms == {"Mine"}


# ── GET /therapy-plans/{id} ───────────────────────────────────────────────────


class TestGetTherapyPlan:
    def test_get_existing_plan(self, client, test_db, fake_user):
        with Session(test_db) as db:
            record = TherapyPlanRecord(
                patient_pseudonym="Test Patient",
                plan_data=json.dumps({"patient_pseudonym": "Test Patient", "total_sessions": 12}),
                user_id=fake_user.id,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            plan_id = record.id

        res = client.get(f"/therapy-plans/{plan_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["patient_pseudonym"] == "Test Patient"
        assert data["total_sessions"] == 12
        assert "_db_id" in data
        assert "created_at" in data

    def test_get_nonexistent_plan(self, client):
        res = client.get("/therapy-plans/99999")
        assert res.status_code == 404

    def test_get_other_users_plan_returns_404(self, client, test_db):
        """A TherapyPlanRecord owned by a different user must not be retrievable."""
        other = User(id=uuid4(), email="other@test.example", password_hash="x")
        with Session(test_db) as db:
            db.add(other)
            db.commit()
            db.refresh(other)
            record = TherapyPlanRecord(
                patient_pseudonym="Theirs",
                plan_data=json.dumps({"patient_pseudonym": "Theirs"}),
                user_id=other.id,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            plan_id = record.id

        res = client.get(f"/therapy-plans/{plan_id}")
        assert res.status_code == 404


# ── PUT /therapy-plans/{id} ───────────────────────────────────────────────────


class TestUpdateTherapyPlan:
    def test_update_own_plan_succeeds(self, client, test_db, fake_user):
        with Session(test_db) as db:
            record = TherapyPlanRecord(
                patient_pseudonym="Old Name",
                plan_data=json.dumps({"patient_pseudonym": "Old Name", "total_sessions": 5}),
                user_id=fake_user.id,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            plan_id = record.id

        updated = {"patient_pseudonym": "New Name", "total_sessions": 20}
        res = client.put(f"/therapy-plans/{plan_id}", json=updated)
        assert res.status_code == 200
        data = res.json()
        # Returns TherapyPlanSummary, not the full plan dict
        assert "id" in data
        assert "created_at" in data

        with Session(test_db) as db:
            saved = db.get(TherapyPlanRecord, plan_id)
            assert saved is not None
            assert json.loads(saved.plan_data)["patient_pseudonym"] == "New Name"

    def test_update_nonexistent_plan(self, client):
        res = client.put("/therapy-plans/99999", json={"patient_pseudonym": "X"})
        assert res.status_code == 404

    def test_update_other_users_plan_returns_404(self, client, test_db):
        """A PUT against another user's plan must 404 (not 403) — no existence leak."""
        other = User(id=uuid4(), email="other@test.example", password_hash="x")
        with Session(test_db) as db:
            db.add(other)
            db.commit()
            db.refresh(other)
            record = TherapyPlanRecord(
                patient_pseudonym="Theirs",
                plan_data=json.dumps({"patient_pseudonym": "Theirs", "total_sessions": 5}),
                user_id=other.id,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            plan_id = record.id

        res = client.put(f"/therapy-plans/{plan_id}", json={"patient_pseudonym": "Hacked"})
        assert res.status_code == 404

        # The other user's record must remain untouched.
        with Session(test_db) as db:
            still_there = db.get(TherapyPlanRecord, plan_id)
            assert still_there is not None
            assert json.loads(still_there.plan_data)["patient_pseudonym"] == "Theirs"
