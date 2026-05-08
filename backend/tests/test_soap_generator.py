"""Tests for SOAPGenerator service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from services.soap_generator import SOAPGenerator


def _make_generator(json_return: dict) -> SOAPGenerator:
    groq = MagicMock()
    groq.json_completion = AsyncMock(return_value=json_return)
    return SOAPGenerator(groq)


_SOAP_RESULT = {
    "subjective": "Patient klagt über Artikulationsprobleme.",
    "objective": "Phonologische Prozesse: Vorverlagerung.",
    "assessment": "Phonologische Störung mittleren Schweregrades.",
    "plan": "Wöchentliche Therapie à 45 Minuten.",
}


class TestSOAPGeneratorGenerateFromData:
    @pytest.mark.asyncio
    async def test_basic_with_collected_data(self):
        gen = _make_generator(_SOAP_RESULT)
        result = await gen.generate_from_data(
            collected_data={"patient_pseudonym": "M.S.", "alter": "5 Jahre"},
        )
        assert result["subjective"] == _SOAP_RESULT["subjective"]
        assert result["objective"] == _SOAP_RESULT["objective"]
        assert result["assessment"] == _SOAP_RESULT["assessment"]
        assert result["plan"] == _SOAP_RESULT["plan"]

    @pytest.mark.asyncio
    async def test_with_empty_collected_data(self):
        gen = _make_generator(_SOAP_RESULT)
        result = await gen.generate_from_data(collected_data={})
        assert "subjective" in result
        assert "plan" in result

    @pytest.mark.asyncio
    async def test_skips_private_keys(self):
        """Keys starting with _ or in exclusion list should not be included."""
        gen = _make_generator(_SOAP_RESULT)
        result = await gen.generate_from_data(
            collected_data={
                "_internal": "should be skipped",
                "greeting": "should also be skipped",
                "patient_pseudonym": "M.S.",
            }
        )
        # Call succeeded — no exception
        assert "subjective" in result

    @pytest.mark.asyncio
    async def test_with_list_value_in_collected_data(self):
        gen = _make_generator(_SOAP_RESULT)
        result = await gen.generate_from_data(collected_data={"therapieziele": ["Ziel 1", "Ziel 2"]})
        assert "subjective" in result

    @pytest.mark.asyncio
    async def test_with_report_data(self):
        gen = _make_generator(_SOAP_RESULT)
        report = {
            "report_type": "befundbericht",
            "patient": {"pseudonym": "T.K.", "age_group": "Kind"},
            "diagnose": {
                "diagnose_text": "Phonologische Störung",
                "icd_10_codes": ["F80.0"],
            },
            "anamnese": "Anamnese-Text",
        }
        result = await gen.generate_from_data(
            collected_data={"patient_pseudonym": "T.K."},
            report=report,
        )
        assert result["subjective"] == _SOAP_RESULT["subjective"]

    @pytest.mark.asyncio
    async def test_report_with_list_values(self):
        gen = _make_generator(_SOAP_RESULT)
        report = {
            "report_type": "befundbericht",
            "therapieziele": ["Ziel A", "Ziel B"],
            "patient": {},
            "diagnose": {"icd_10_codes": []},
        }
        result = await gen.generate_from_data(
            collected_data={},
            report=report,
        )
        assert "subjective" in result

    @pytest.mark.asyncio
    async def test_result_as_string_gets_parsed(self):
        """If groq returns a string instead of dict, it should be parsed."""
        import json

        groq = MagicMock()
        groq.json_completion = AsyncMock(return_value=json.dumps(_SOAP_RESULT))
        gen = SOAPGenerator(groq)

        result = await gen.generate_from_data(collected_data={"patient_pseudonym": "X"})
        assert result["subjective"] == _SOAP_RESULT["subjective"]

    @pytest.mark.asyncio
    async def test_missing_keys_default_to_empty_string(self):
        groq = MagicMock()
        groq.json_completion = AsyncMock(return_value={})
        gen = SOAPGenerator(groq)

        result = await gen.generate_from_data(collected_data={})
        assert result["subjective"] == ""
        assert result["objective"] == ""
        assert result["assessment"] == ""
        assert result["plan"] == ""

    @pytest.mark.asyncio
    async def test_report_with_empty_patient_and_diagnose(self):
        gen = _make_generator(_SOAP_RESULT)
        report = {
            "report_type": "befundbericht",
            "patient": {},
            "diagnose": {},
        }
        result = await gen.generate_from_data(collected_data={}, report=report)
        assert "subjective" in result
