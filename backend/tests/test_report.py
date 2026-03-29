"""Tests for report generation endpoint."""


def test_generate_report(client, session_id, mock_groq):
    mock_groq["json"].return_value = {
        "report_type": "befundbericht",
        "patient": {"pseudonym": "M.S.", "age_group": "Kind", "gender": "männlich"},
        "diagnose": {
            "icd_10_codes": ["F80.0"],
            "indikationsschluessel": "SP1",
            "diagnose_text": "Sprachentwicklungsstörung",
        },
        "anamnese": "Laut Angaben der Eltern begann die Sprachentwicklung verspätet.",
        "befund": "Im Bereich der Phonologie zeigt sich eine Vorverlagerung.",
        "therapieindikation": "Eine logopädische Behandlung ist indiziert.",
        "therapieziele": ["Erweiterung des Lautinventars"],
        "empfehlung": "Weiterführung der Therapie wird empfohlen.",
    }

    res = client.post(f"/sessions/{session_id}/generate")
    assert res.status_code == 200
    data = res.json()
    assert data["report_type"] == "befundbericht"
    assert "anamnese" in data


def test_generate_report_session_not_found(client, mock_groq):
    res = client.post("/sessions/nonexistent/generate")
    assert res.status_code == 404


def test_get_report_not_generated(client, session_id):
    res = client.get(f"/sessions/{session_id}/report")
    assert res.status_code == 404


def test_get_report_after_generation(client, session_id, mock_groq):
    mock_groq["json"].return_value = {
        "report_type": "befundbericht",
        "patient": {"pseudonym": "T.P.", "age_group": "Erwachsen", "gender": None},
        "diagnose": {
            "icd_10_codes": [],
            "indikationsschluessel": "",
            "diagnose_text": "Dysarthrie",
        },
        "anamnese": "Anamnese-Text",
        "befund": "Befund-Text",
        "therapieindikation": "Indikation",
        "therapieziele": [],
        "empfehlung": "Empfehlung",
    }

    client.post(f"/sessions/{session_id}/generate")
    res = client.get(f"/sessions/{session_id}/report")
    assert res.status_code == 200
    assert res.json()["report_type"] == "befundbericht"
