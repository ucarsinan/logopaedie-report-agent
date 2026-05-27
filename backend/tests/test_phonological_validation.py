"""M-3: /analysis/phonological-text must reject malformed word pairs with a clean
422, not crash with a 500 on a missing/renamed key.
"""

from __future__ import annotations


def test_wrong_key_returns_422_not_500(client, mock_groq):
    """A pair using the wrong field name ('produced') must fail validation, not 500."""
    res = client.post(
        "/analysis/phonological-text",
        json=[{"target": "Katze", "produced": "Tatze"}],  # 'produced' != required 'production'
    )
    assert res.status_code == 422


def test_missing_target_returns_422(client, mock_groq):
    res = client.post(
        "/analysis/phonological-text",
        json=[{"production": "Tatze"}],
    )
    assert res.status_code == 422


def test_valid_pairs_still_accepted(client, mock_groq):
    mock_groq["json"].return_value = {
        "items": [{"target_word": "Katze", "production": "Tatze", "processes": [], "severity": "leicht"}],
        "summary": "ok",
        "age_appropriate": True,
        "recommended_focus": [],
    }
    res = client.post(
        "/analysis/phonological-text",
        json=[{"target": "Katze", "production": "Tatze"}],
    )
    assert res.status_code == 200
    assert res.json()["items"][0]["target_word"] == "Katze"
