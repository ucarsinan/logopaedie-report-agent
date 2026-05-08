"""Integration test: full report lifecycle — session → chat → generate → retrieve."""

from __future__ import annotations

from unittest.mock import MagicMock

BEFUNDBERICHT_PAYLOAD = {
    "report_type": "befundbericht",
    "patient": {"pseudonym": "M.S.", "age_group": "Kind", "gender": "männlich"},
    "diagnose": {
        "icd_10_codes": ["F80.0"],
        "indikationsschluessel": "SP1",
        "diagnose_text": "Sprachentwicklungsstörung",
    },
    "anamnese": "Verspätete Sprachentwicklung laut Eltern.",
    "befund": "Vorverlagerung im phonologischen Bereich.",
    "therapieindikation": "Logopädische Behandlung indiziert.",
    "therapieziele": ["Erweiterung des Lautinventars"],
    "empfehlung": "Fortsetzung der Therapie empfohlen.",
}


def test_full_report_lifecycle(client, mock_groq, mock_redis, fake_user):
    """Session create → chat → generate → GET session report → appears in report list."""
    # Override get_optional_user so generate_report saves to DB (it uses the optional dep, not current_user)
    from dependencies import get_optional_user
    from main import app

    app.dependency_overrides[get_optional_user] = lambda: fake_user

    # --- Setup Redis mock to persist session state ---
    _store: dict[str, object] = {}

    def fake_set(key, value, **kwargs):
        _store[key] = value

    def fake_get(key):
        return _store.get(key)

    mock_redis.set = MagicMock(side_effect=fake_set)
    mock_redis.get = MagicMock(side_effect=fake_get)

    # 1. Create session — greeting is static (no chat LLM call needed)
    resp = client.post("/sessions")
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    # 2. Send a chat message
    mock_groq["chat"].return_value = "Verstanden — ein Befundbericht für ein Kind."
    # json_completion is used by _extract_data after each chat turn.
    # Include patient_pseudonym in data so the report generator can use it as pseudonym.
    mock_groq["json"].return_value = {
        "phase": "patient_info",
        "report_type": "befundbericht",
        "collected_fields": ["report_type"],
        "is_complete": False,
        "data": {"patient_pseudonym": "M.S."},
    }
    resp = client.post(f"/sessions/{session_id}/chat", json={"message": "Befundbericht bitte"})
    assert resp.status_code == 200
    assert resp.json()["message"] == "Verstanden — ein Befundbericht für ein Kind."

    # 3. Generate report — json_completion now returns the report content
    mock_groq["json"].return_value = BEFUNDBERICHT_PAYLOAD
    resp = client.post(f"/sessions/{session_id}/generate")
    assert resp.status_code == 200
    report_data = resp.json()
    assert report_data["report_type"] == "befundbericht"
    assert "anamnese" in report_data

    # 4. Retrieve report from session
    resp = client.get(f"/sessions/{session_id}/report")
    assert resp.status_code == 200
    assert resp.json()["report_type"] == "befundbericht"

    # 5. Report appears in list
    resp = client.get("/reports")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert any(r["pseudonym"] == "M.S." for r in items)

    # 6. Report retrievable by ID
    report_id = next(r["id"] for r in items if r["pseudonym"] == "M.S.")
    resp = client.get(f"/reports/{report_id}")
    assert resp.status_code == 200
    assert resp.json()["report_type"] == "befundbericht"

    # Cleanup override added in this test
    app.dependency_overrides.pop(get_optional_user, None)


def test_report_not_accessible_before_generation(client, session_id):
    resp = client.get(f"/sessions/{session_id}/report")
    assert resp.status_code == 404


def test_report_list_empty_initially(client):
    resp = client.get("/reports")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    assert resp.json()["items"] == []
