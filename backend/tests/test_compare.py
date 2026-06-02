"""Tests for report comparison endpoint and ReportComparator service."""

import io
from unittest.mock import AsyncMock

import pytest

from models.schemas import ReportComparison
from services.report_comparator import ReportComparator


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


@pytest.mark.asyncio
async def test_compare_files_identical_reports_yields_no_diff_shape():
    """``compare_files`` with two byte-identical .txt reports must still
    return a well-formed ``ReportComparison``. When the LLM (mocked) reports
    "no changes," the service preserves the empty-items / empty-issues
    shape — callers depend on the structure, not on items being non-empty."""
    groq = AsyncMock()
    groq.json_completion = AsyncMock(
        return_value={
            "items": [],
            "overall_progress": "Keine Veränderungen zwischen beiden Berichten erkennbar.",
            "remaining_issues": [],
            "recommendation": "Status quo beibehalten.",
        }
    )
    comparator = ReportComparator(groq)
    same = b"Befund: Phonologische Prozesse altersgemaess. Wortschatz im Normbereich."
    result = await comparator.compare_files(
        initial_content=same,
        initial_filename="initial.txt",
        initial_content_type="text/plain",
        current_content=same,
        current_filename="current.txt",
        current_content_type="text/plain",
    )
    assert isinstance(result, ReportComparison)
    assert result.items == []
    assert result.remaining_issues == []
    assert "Keine Veränderungen" in result.overall_progress
    assert result.recommendation == "Status quo beibehalten."
    # The Groq call was made exactly once with both report bodies in the prompt.
    assert groq.json_completion.call_count == 1
    messages_arg = groq.json_completion.call_args.args[0]
    user_content = messages_arg[0]["content"]
    assert "Befund: Phonologische Prozesse" in user_content


@pytest.mark.asyncio
async def test_compare_files_single_divergent_field_surfaces_in_diff():
    """``compare_files`` with two reports differing in one section must
    surface that section as a ``ComparisonItem`` in the result. Verifies
    the bytes→text→LLM→Pydantic pipeline preserves field-level changes
    end-to-end and that the ``change`` enum value passes through unmodified."""
    groq = AsyncMock()
    groq.json_completion = AsyncMock(
        return_value={
            "items": [
                {
                    "category": "Phonologie",
                    "initial_finding": "Vorverlagerung /k/ → /t/",
                    "current_finding": "Korrekte Produktion von /k/",
                    "change": "verbessert",
                    "details": "P.O.P.T. abgeschlossen.",
                }
            ],
            "overall_progress": "Phonologischer Fortschritt erreicht.",
            "remaining_issues": [],
            "recommendation": "Therapie beenden.",
        }
    )
    comparator = ReportComparator(groq)
    initial = b"Erstbefund: Vorverlagerung /k/ -> /t/. Wortschatz altersgemaess."
    current = b"Aktuell: /k/ korrekt im Anlaut. Wortschatz altersgemaess."
    result = await comparator.compare_files(
        initial_content=initial,
        initial_filename="initial.txt",
        initial_content_type="text/plain",
        current_content=current,
        current_filename="current.txt",
        current_content_type="text/plain",
    )
    assert isinstance(result, ReportComparison)
    assert len(result.items) == 1
    item = result.items[0]
    assert item.category == "Phonologie"
    assert item.change == "verbessert"
    assert "Vorverlagerung" in item.initial_finding
    assert "Korrekte Produktion" in item.current_finding
    assert result.recommendation == "Therapie beenden."
    # Confirm both file bodies reached the LLM prompt (sanity for the
    # bytes→extract_text→compare wiring).
    user_content = groq.json_completion.call_args.args[0][0]["content"]
    assert "Erstbefund" in user_content
    assert "Aktuell" in user_content
