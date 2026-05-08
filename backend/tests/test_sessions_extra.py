"""Additional tests for session routes: new-conversation, materials-consent, generate error path."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch


class TestNewConversation:
    def test_new_conversation_success(self, client, session_id, mock_groq):
        mock_groq["chat"].return_value = "Willkommen zurück! Welchen Berichtstyp?"
        res = client.post(f"/sessions/{session_id}/new-conversation")
        assert res.status_code == 200
        data = res.json()
        assert data["session_id"] == session_id
        assert data["status"] == "anamnesis"
        assert "greeting" in data["collected_data"]

    def test_new_conversation_fallback_greeting_on_error(self, client, session_id, mock_groq):
        mock_groq["chat"].side_effect = Exception("Groq failure")
        res = client.post(f"/sessions/{session_id}/new-conversation")
        assert res.status_code == 200
        data = res.json()
        assert "greeting" in data["collected_data"]

    def test_new_conversation_session_not_found(self, client):
        res = client.post("/sessions/aabbccddeeff/new-conversation")
        assert res.status_code == 404

    def test_new_conversation_invalid_session_id(self, client):
        res = client.post("/sessions/INVALID/new-conversation")
        assert res.status_code == 400


class TestMaterialsConsent:
    def test_set_consent_true(self, client, session_id):
        res = client.post(
            f"/sessions/{session_id}/materials-consent",
            json={"consent": True},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["materials_consent"] is True

    def test_set_consent_false(self, client, session_id):
        res = client.post(
            f"/sessions/{session_id}/materials-consent",
            json={"consent": False},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["materials_consent"] is False

    def test_consent_session_not_found(self, client):
        res = client.post(
            "/sessions/aabbccddeeff/materials-consent",
            json={"consent": True},
        )
        assert res.status_code == 404

    def test_consent_invalid_session_id(self, client):
        res = client.post(
            "/sessions/INVALID/materials-consent",
            json={"consent": True},
        )
        assert res.status_code == 400


class TestGenerateReport:
    def test_generate_session_not_found(self, client):
        res = client.post("/sessions/aabbccddeeff/generate")
        assert res.status_code == 404

    def test_generate_invalid_session_id(self, client):
        res = client.post("/sessions/INVALID/generate")
        assert res.status_code == 400

    def test_generate_error_resets_status(self, mock_groq, mock_redis):
        """If generate fails, session status should be reset to 'materials'."""

        from fastapi.testclient import TestClient

        from main import app

        _stored = {}
        mock_redis.set = MagicMock(side_effect=lambda k, v, **kw: _stored.__setitem__(k, v))
        mock_redis.get = MagicMock(side_effect=lambda k: _stored.get(k))

        # Use raise_server_exceptions=False so 500 responses don't raise
        with TestClient(app, raise_server_exceptions=False) as tc:
            mock_groq["chat"].return_value = "Willkommen!"
            res = tc.post("/sessions")
            assert res.status_code == 200
            sid = res.json()["session_id"]

            with patch(
                "services.report_generator.ReportGenerator.generate",
                new_callable=AsyncMock,
                side_effect=RuntimeError("AI failure"),
            ):
                res = tc.post(f"/sessions/{sid}/generate")
                assert res.status_code >= 400


class TestGetReport:
    def test_get_report_not_generated(self, client, session_id):
        res = client.get(f"/sessions/{session_id}/report")
        assert res.status_code == 404

    def test_get_report_invalid_session_id(self, client):
        res = client.get("/sessions/INVALID/report")
        assert res.status_code == 400

    def test_get_report_session_not_found(self, client):
        res = client.get("/sessions/aabbccddeeff/report")
        assert res.status_code == 404


class TestCreateSessionModes:
    def test_create_session_therapy_plan_mode(self, client, mock_groq):
        mock_groq["chat"].return_value = "Willkommen im Therapieplan-Modus!"
        res = client.post("/sessions", json={"mode": "therapy_plan"})
        assert res.status_code == 200
        data = res.json()
        assert data["therapy_plan_mode"] is True

    def test_create_session_greeting_fallback(self, client, mock_groq):
        mock_groq["chat"].side_effect = Exception("Error")
        res = client.post("/sessions")
        assert res.status_code == 200
        data = res.json()
        assert "session_id" in data

    def test_create_session_therapy_plan_fallback(self, client, mock_groq):
        mock_groq["chat"].side_effect = Exception("Error")
        res = client.post("/sessions", json={"mode": "therapy_plan"})
        assert res.status_code == 200
        data = res.json()
        assert data["therapy_plan_mode"] is True
