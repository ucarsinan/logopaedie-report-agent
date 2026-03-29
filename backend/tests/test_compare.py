"""Tests for report comparison endpoint."""

import io


def test_compare_reports(client, mock_groq):
    mock_groq["json"].return_value = {
        "items": [
            {
                "category": "Phonologie",
                "initial_finding": "Vorverlagerung /k/ → /t/",
                "current_finding": "Korrekte Produktion von /k/ im Anlaut",
                "change": "verbessert",
                "details": "Deutliche Verbesserung nach 20 Sitzungen P.O.P.T.",
            },
            {
                "category": "Wortschatz",
                "initial_finding": "Unterdurchschnittlich",
                "current_finding": "Altersgemäß",
                "change": "verbessert",
                "details": "Wortschatzexpansion durch semantische Elaboration.",
            },
        ],
        "overall_progress": "Insgesamt deutliche Fortschritte in allen Bereichen.",
        "remaining_issues": ["Konsonantenverbindungen im Inlaut"],
        "recommendation": "Weiterführung der Therapie für 10 weitere Sitzungen.",
    }

    initial = b"Erstbefund: Vorverlagerung, eingeschraenkter Wortschatz."
    current = b"Aktuell: Korrekte Velarlaute, altersgemaeszer Wortschatz."

    res = client.post(
        "/analysis/compare",
        files={
            "initial_report": ("initial.txt", io.BytesIO(initial), "text/plain"),
            "current_report": ("current.txt", io.BytesIO(current), "text/plain"),
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 2
    assert data["items"][0]["change"] == "verbessert"
    assert len(data["remaining_issues"]) == 1
    assert "Weiterführung" in data["recommendation"]
