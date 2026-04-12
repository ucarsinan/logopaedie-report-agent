"""Tests for therapy plan generation endpoint."""


def test_generate_therapy_plan(client, session_id, mock_groq):
    mock_groq["json"].return_value = {
        "patient_pseudonym": "M.S.",
        "diagnose_text": "Sprachentwicklungsstörung (F80.0)",
        "plan_phases": [
            {
                "phase_name": "Aufbauphase",
                "duration": "10 Sitzungen",
                "goals": [
                    {
                        "icf_code": "b320",
                        "goal_text": "Korrekte Produktion von /k/ und /g/ in Anlautposition",
                        "methods": ["P.O.P.T.", "Minimalpaartherapie"],
                        "milestones": ["Lautanbahnung", "Silbenebene", "Wortebene"],
                        "timeframe": "Sitzung 1-10",
                    }
                ],
            }
        ],
        "frequency": "2x pro Woche, 45 Min.",
        "total_sessions": 20,
        "elternberatung": "Korrektives Feedback im Alltag einsetzen.",
        "haeusliche_uebungen": ["Minimalpaare üben", "Bildkarten benennen"],
    }

    res = client.post(f"/sessions/{session_id}/therapy-plan")
    assert res.status_code == 200
    data = res.json()
    assert data["patient_pseudonym"] == "M.S."
    assert len(data["plan_phases"]) == 1
    assert data["plan_phases"][0]["goals"][0]["icf_code"] == "b320"
    assert data["total_sessions"] == 20
    assert len(data["haeusliche_uebungen"]) == 2


def test_therapy_plan_session_not_found(client, mock_groq):
    res = client.post("/sessions/aabbccddeeff/therapy-plan")
    assert res.status_code == 404
