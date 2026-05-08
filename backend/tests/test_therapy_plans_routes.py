"""Tests for therapy plan save/list/get/update endpoints."""

from __future__ import annotations

import json

from sqlmodel import Session

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
                )
            )
            db.add(
                TherapyPlanRecord(
                    patient_pseudonym="C.D.",
                    plan_data=json.dumps({"patient_pseudonym": "C.D."}),
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


# ── GET /therapy-plans/{id} ───────────────────────────────────────────────────


class TestGetTherapyPlan:
    def test_get_existing_plan(self, client, test_db):
        with Session(test_db) as db:
            record = TherapyPlanRecord(
                patient_pseudonym="Test Patient",
                plan_data=json.dumps({"patient_pseudonym": "Test Patient", "total_sessions": 12}),
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


# ── PUT /therapy-plans/{id} ───────────────────────────────────────────────────


class TestUpdateTherapyPlan:
    def test_update_plan(self, client, test_db):
        with Session(test_db) as db:
            record = TherapyPlanRecord(
                patient_pseudonym="Old Name",
                plan_data=json.dumps({"patient_pseudonym": "Old Name", "total_sessions": 5}),
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

    def test_update_nonexistent_plan(self, client):
        res = client.put("/therapy-plans/99999", json={"patient_pseudonym": "X"})
        assert res.status_code == 404
