"""C-2: the report-generation prompt must instruct the model not to fabricate
clinical facts (frequencies, durations, session counts, percentages, test results).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from services.report_generator import ReportGenerator
from services.session_store import Session


def _session(report_type: str = "befundbericht") -> Session:
    s = Session("abcdef012345")
    s.report_type = report_type
    s.collected_data = {
        "patient_pseudonym": "Test P.",
        "age_group": "kind",
        "diagnose_text": "phonologische Störung",
    }
    return s


@pytest.mark.asyncio
async def test_prompt_forbids_fabricating_clinical_values():
    captured: dict[str, str] = {}

    async def fake_json(messages, system_prompt, **kwargs):
        captured["system_prompt"] = system_prompt
        return {"anamnese": "", "befund": "", "empfehlung": ""}

    from services.groq_client import GroqService

    gen = ReportGenerator(GroqService())
    with patch.object(GroqService, "json_completion", new=AsyncMock(side_effect=fake_json)):
        await gen.generate(_session())

    prompt = captured["system_prompt"].lower()
    # The guardrail must explicitly forbid inventing the values we observed being hallucinated.
    assert "erfinde" in prompt
    for term in ("frequenz", "dauer", "sitzung", "prozent"):
        assert term in prompt, f"guardrail should mention '{term}'"


@pytest.mark.asyncio
async def test_guardrail_present_for_all_report_types():
    captured: dict[str, str] = {}

    async def fake_json(messages, system_prompt, **kwargs):
        captured["system_prompt"] = system_prompt
        return {}

    from services.groq_client import GroqService

    gen = ReportGenerator(GroqService())
    for rt in ("befundbericht", "therapiebericht_kurz", "therapiebericht_lang", "abschlussbericht"):
        with patch.object(GroqService, "json_completion", new=AsyncMock(side_effect=fake_json)):
            await gen.generate(_session(rt))
        assert "erfinde" in captured["system_prompt"].lower(), f"missing guardrail for {rt}"
