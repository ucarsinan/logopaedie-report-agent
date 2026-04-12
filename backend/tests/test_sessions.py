"""Tests for session management and chat endpoints."""


def test_create_session(client, mock_groq):
    mock_groq["chat"].return_value = "Hallo! Welchen Berichtstyp möchten Sie erstellen?"
    res = client.post("/sessions")
    assert res.status_code == 200
    data = res.json()
    assert "session_id" in data
    assert data["status"] == "anamnesis"


def test_get_session(client, session_id):
    res = client.get(f"/sessions/{session_id}")
    assert res.status_code == 200
    assert res.json()["session_id"] == session_id


def test_get_session_not_found(client):
    res = client.get("/sessions/aabbccddeeff")
    assert res.status_code == 404


def test_chat(client, session_id, mock_groq):
    mock_groq["chat"].return_value = "Verstanden, ein Befundbericht."
    mock_groq["json"].return_value = {
        "report_type": "befundbericht",
        "current_phase": "patient_info",
        "collected_fields": ["report_type"],
    }

    res = client.post(
        f"/sessions/{session_id}/chat",
        json={"message": "Befundbericht bitte"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "message" in data
    assert data["message"] == "Verstanden, ein Befundbericht."


def test_chat_empty_message(client, session_id):
    res = client.post(
        f"/sessions/{session_id}/chat",
        json={"message": ""},
    )
    assert res.status_code == 400


def test_chat_session_not_found(client, mock_groq):
    res = client.post(
        "/sessions/aabbccddeeff/chat",
        json={"message": "Hallo"},
    )
    assert res.status_code == 404
