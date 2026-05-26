"""Tests for the phrasing turn and orchestration in AnamnesisEngine."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from services.anamnesis_catalog import Slot
from services.anamnesis_engine import AnamnesisEngine


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
