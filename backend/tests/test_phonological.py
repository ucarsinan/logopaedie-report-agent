"""Tests for phonological analysis endpoints."""


def test_analyze_phonological_text(client, mock_groq):
    mock_groq["json"].return_value = {
        "items": [
            {
                "target_word": "Kanne",
                "production": "Tanne",
                "processes": ["Vorverlagerung /k/ → /t/"],
                "severity": "mittel",
            }
        ],
        "summary": "Es zeigt sich eine konsistente Vorverlagerung.",
        "age_appropriate": False,
        "recommended_focus": ["Velarlaute /k/ und /g/"],
    }

    res = client.post(
        "/analysis/phonological-text",
        json=[{"target": "Kanne", "production": "Tanne"}],
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["target_word"] == "Kanne"
    assert data["age_appropriate"] is False
    assert len(data["recommended_focus"]) == 1


def test_analyze_phonological_text_with_age(client, mock_groq):
    mock_groq["json"].return_value = {
        "items": [
            {
                "target_word": "Schule",
                "production": "Sule",
                "processes": ["Deaffrizierung /ʃ/ → /s/"],
                "severity": "leicht",
            }
        ],
        "summary": "Altersgemäße Vereinfachung.",
        "age_appropriate": True,
        "recommended_focus": [],
    }

    res = client.post(
        "/analysis/phonological-text?child_age=3%3B0",
        json=[{"target": "Schule", "production": "Sule"}],
    )
    assert res.status_code == 200
    assert res.json()["age_appropriate"] is True
