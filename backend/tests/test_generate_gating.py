"""H-4: generating from an incomplete anamnesis must not happen silently.

The report is still produced (so a therapist can preview / iterate), but the
response must explicitly flag which required fields were never collected, so the
gap is visible instead of being silently filled in.
"""

from __future__ import annotations


def _report_payload() -> dict:
    return {
        "report_type": "befundbericht",
        "anamnese": "",
        "befund": "",
        "diagnose_text": "",
        "therapieindikation": "",
        "therapieziele": [],
        "empfehlung": "",
    }


def test_generate_flags_missing_required_fields(client, session_id, mock_groq):
    """An empty session is missing required fields → response must warn about them."""
    mock_groq["json"].return_value = _report_payload()

    res = client.post(f"/sessions/{session_id}/generate")
    assert res.status_code == 200
    data = res.json()
    warnings = data.get("_warnings")
    assert warnings is not None, "incomplete anamnesis must produce a warning"
    missing = warnings["missing_required_fields"]
    # befundbericht requires these — none were collected in an empty session.
    assert "patient_pseudonym" in missing
    assert "diagnose_text" in missing


def test_generate_no_warning_when_required_fields_present(client, session_id, mock_groq):
    """When all required fields are collected, no missing-field warning is attached."""
    mock_groq["json"].return_value = _report_payload()

    from services.session_store import store

    session = store.get(session_id)
    session.report_type = "befundbericht"
    session.collected_data.update(
        {
            "report_type": "befundbericht",
            "patient_pseudonym": "Max M.",
            "age_group": "kind",
            "indikationsschluessel": "SP3",
            "anamnese_persoenlich": "unauffällig",
            "diagnose_text": "phonologische Störung",
        }
    )
    store.save(session)

    res = client.post(f"/sessions/{session_id}/generate")
    assert res.status_code == 200
    warnings = res.json().get("_warnings")
    assert not warnings or not warnings.get("missing_required_fields")
