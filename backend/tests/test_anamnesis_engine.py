"""Tests for the phrasing turn and orchestration in AnamnesisEngine."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from services.anamnesis_catalog import Slot
from services.anamnesis_engine import AnamnesisEngine
from services.session_store import Session


@pytest.mark.asyncio
async def test_phrase_turn_appends_options_line_for_choice_slots():
    groq = AsyncMock()
    groq.chat_completion = AsyncMock(return_value="Verstanden. Welche Altersgruppe?")
    engine = AnamnesisEngine(groq)
    slot = Slot("age_group", "nach der Altersgruppe", options=["Kind", "Jugendliche/r", "Erwachsene/r"])

    out = await engine._phrase_turn("Befundbericht", slot, recent=[])

    assert out.endswith("– Kind – Jugendliche/r – Erwachsene/r")
    args = groq.chat_completion.call_args
    sent_messages = args.args[0] if args.args else args.kwargs["messages"]
    assert len(sent_messages) <= 3


@pytest.mark.asyncio
async def test_phrase_turn_falls_back_to_deterministic_text_on_llm_error():
    groq = AsyncMock()
    groq.chat_completion = AsyncMock(side_effect=RuntimeError("model down"))
    engine = AnamnesisEngine(groq)
    slot = Slot("diagnose_text", "nach der zusammenfassenden Diagnose")

    out = await engine._phrase_turn("letzte Antwort", slot, recent=[])

    assert "Diagnose" in out  # deterministic fallback derived from slot.ask


def _session(report_type, indikation, age, collected):
    s = Session("probe00000000")
    s.report_type = report_type
    s.collected_data = {"report_type": report_type, "indikationsschluessel": indikation, "age_group": age, **collected}
    return s


def test_build_summary_lists_collected_values_and_asks_confirmation():
    engine = AnamnesisEngine(AsyncMock())
    s = _session("befundbericht", "RE1", "jugendlich", {"patient_pseudonym": "DL"})
    text = engine._build_summary(s)
    assert "DL" in text
    assert "?" in text  # asks for confirmation
    assert "Lassen Sie uns" not in text  # no preamble parroting


def test_is_affirmation_recognizes_yes_variants():
    engine = AnamnesisEngine(AsyncMock())
    assert engine._is_affirmation("ja, passt")
    assert engine._is_affirmation("Stimmt so")
    assert not engine._is_affirmation("nein, das Alter ist falsch")
