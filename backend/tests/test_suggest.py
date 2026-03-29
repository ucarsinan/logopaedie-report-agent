"""Tests for text suggestion endpoint."""


def test_suggest_text(client, mock_groq):
    mock_groq["json"].return_value = {
        "suggestions": [
            "eine konsistente Vorverlagerung der velaren Plosive.",
            "eine konsistente Vorverlagerung der velaren Plosive /k/ und /g/ zu /t/ und /d/ in allen Wortpositionen.",
            "eine konsistente Vorverlagerung der velaren Plosive /k/ und /g/ zu /t/ und /d/ in allen Wortpositionen. Darüber hinaus zeigten sich Reduktionen von Konsonantenverbindungen im Anlaut. Die Nachsprechleistung war dabei deutlich besser als die Spontansprache.",
        ]
    }

    res = client.post(
        "/suggest",
        json={
            "text": "Die phonologische Bewertung ergab ",
            "report_type": "befundbericht",
            "disorder": "SP1",
            "section": "befund",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["suggestions"]) == 3
    # Suggestions should increase in length
    assert len(data["suggestions"][0]) < len(data["suggestions"][2])


def test_suggest_empty_text(client, mock_groq):
    res = client.post(
        "/suggest",
        json={"text": "   "},
    )
    assert res.status_code == 400
