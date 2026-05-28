"""Tests for PhonologicalAnalyzer service (both text and audio paths)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from models.schemas import PhonologicalAnalysis
from services.phonological_analyzer import PhonologicalAnalyzer

_JSON_RESULT = {
    "items": [
        {
            "target_word": "Kanne",
            "production": "Tanne",
            "processes": ["Vorverlagerung /k/ → /t/"],
            "severity": "mittel",
        }
    ],
    "summary": "Konsistente Vorverlagerung.",
    "age_appropriate": False,
    "recommended_focus": ["Velarlaute"],
}


def _make_analyzer(json_return=None, transcribe_side_effect=None):
    groq = MagicMock()
    groq.json_completion = AsyncMock(return_value=json_return or _JSON_RESULT)
    if transcribe_side_effect is not None:
        groq.transcribe_audio = AsyncMock(side_effect=transcribe_side_effect)
    else:
        # Default: first call returns target words, second returns production words
        groq.transcribe_audio = AsyncMock(side_effect=["Kanne Schule", "Tanne Sule"])
    return PhonologicalAnalyzer(groq)


class TestAnalyzeText:
    @pytest.mark.asyncio
    async def test_basic_analysis(self):
        analyzer = _make_analyzer()
        result = await analyzer.analyze(word_pairs=[{"target": "Kanne", "production": "Tanne"}])
        assert isinstance(result, PhonologicalAnalysis)
        assert len(result.items) == 1
        assert result.items[0].target_word == "Kanne"
        assert result.summary == "Konsistente Vorverlagerung."
        assert result.age_appropriate is False
        assert result.recommended_focus == ["Velarlaute"]

    @pytest.mark.asyncio
    async def test_analysis_with_age(self):
        analyzer = _make_analyzer()
        result = await analyzer.analyze(
            word_pairs=[{"target": "Schule", "production": "Sule"}],
            child_age="3;6",
        )
        assert isinstance(result, PhonologicalAnalysis)

    @pytest.mark.asyncio
    async def test_empty_result(self):
        groq = MagicMock()
        groq.json_completion = AsyncMock(return_value={})
        analyzer = PhonologicalAnalyzer(groq)

        result = await analyzer.analyze(word_pairs=[])
        assert result.items == []
        assert result.summary == ""
        assert result.age_appropriate is True
        assert result.recommended_focus == []

    @pytest.mark.asyncio
    async def test_llm_returns_null_age_appropriate(self):
        # Regression: when no child_age is provided, the LLM may emit
        # `"age_appropriate": null` rather than omitting the key. The previous
        # code (`data.get("age_appropriate", True)`) only defaulted on a
        # missing key, so the None reached Pydantic and raised 500.
        groq = MagicMock()
        groq.json_completion = AsyncMock(
            return_value={
                "items": [
                    {
                        "target_word": "fisch",
                        "production": "fis",
                        "processes": [],
                        "severity": "leicht",
                    }
                ],
                "summary": "Ohne Altersangabe nicht abschließend beurteilbar.",
                "age_appropriate": None,
                "recommended_focus": [],
            }
        )
        analyzer = PhonologicalAnalyzer(groq)

        result = await analyzer.analyze(word_pairs=[{"target": "fisch", "production": "fis"}])

        assert isinstance(result, PhonologicalAnalysis)
        assert result.age_appropriate is True

    @pytest.mark.asyncio
    async def test_severity_defaults(self):
        groq = MagicMock()
        groq.json_completion = AsyncMock(
            return_value={
                "items": [
                    {
                        "target_word": "Test",
                        "production": "Tess",
                        # No severity field → default
                    }
                ],
                "summary": "",
                "age_appropriate": True,
                "recommended_focus": [],
            }
        )
        analyzer = PhonologicalAnalyzer(groq)
        result = await analyzer.analyze(word_pairs=[{"target": "Test", "production": "Tess"}])
        assert result.items[0].severity == "leicht"


class TestAnalyzeAudio:
    @pytest.mark.asyncio
    async def test_basic_audio_analysis(self, tmp_path):
        target_path = str(tmp_path / "target.wav")
        prod_path = str(tmp_path / "prod.wav")

        analyzer = _make_analyzer()
        result = await analyzer.analyze_audio(target_path, prod_path)

        assert isinstance(result, PhonologicalAnalysis)
        # transcribe_audio was called twice
        assert analyzer._groq.transcribe_audio.call_count == 2

    @pytest.mark.asyncio
    async def test_audio_with_child_age(self, tmp_path):
        target_path = str(tmp_path / "t.wav")
        prod_path = str(tmp_path / "p.wav")

        analyzer = _make_analyzer()
        result = await analyzer.analyze_audio(target_path, prod_path, child_age="4;0")
        assert isinstance(result, PhonologicalAnalysis)

    @pytest.mark.asyncio
    async def test_audio_unequal_word_counts(self, tmp_path):
        """Production has fewer words than target → missing words get empty string."""
        target_path = str(tmp_path / "t.wav")
        prod_path = str(tmp_path / "p.wav")

        groq = MagicMock()
        groq.json_completion = AsyncMock(return_value=_JSON_RESULT)
        # Target has 3 words, production has 1
        groq.transcribe_audio = AsyncMock(side_effect=["Kanne Schule Baum", "Tanne"])
        analyzer = PhonologicalAnalyzer(groq)

        result = await analyzer.analyze_audio(target_path, prod_path)
        # analyze() should be called with 3 pairs, last two with empty production
        assert isinstance(result, PhonologicalAnalysis)
