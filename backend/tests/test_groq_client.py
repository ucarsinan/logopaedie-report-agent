"""Tests for GroqService (groq_client.py) — mocked at the AsyncGroq level."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from exceptions import (
    AIServiceError,
    ModelExhaustedError,
    RateLimitError,
    ReportGenerationError,
    TranscriptionError,
)
from services.groq_client import GroqService, _is_rate_limit_or_decommissioned

# ── Helper ─────────────────────────────────────────────────────────────────────


def _make_service() -> GroqService:
    """Return a GroqService with a mocked AsyncGroq client."""
    svc = GroqService.__new__(GroqService)
    svc.client = MagicMock()
    return svc


def _chat_response(text: str):
    """Build a minimal chat-completion response mock."""
    choice = MagicMock()
    choice.message.content = text
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _make_rate_limit_error() -> Exception:
    """Create a real groq.RateLimitError (requires httpx.Request + Response)."""
    from groq import RateLimitError as GroqRateLimitError

    request = httpx.Request("GET", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(429, request=request)
    return GroqRateLimitError("rate limit exceeded", response=response, body=None)


# ── _is_rate_limit_or_decommissioned ──────────────────────────────────────────


class TestIsRateLimitOrDecommissioned:
    def test_groq_rate_limit_error(self):
        exc = _make_rate_limit_error()
        assert _is_rate_limit_or_decommissioned(exc) is True

    def test_api_status_error_429(self):
        from groq import APIStatusError

        request = httpx.Request("GET", "https://api.groq.com")
        response = httpx.Response(429, request=request)
        exc = APIStatusError("error", response=response, body=None)
        assert _is_rate_limit_or_decommissioned(exc) is True

    def test_decommissioned_in_message(self):
        exc = Exception("model_decommissioned: please use another model")
        assert _is_rate_limit_or_decommissioned(exc) is True

    def test_regular_exception_returns_false(self):
        assert _is_rate_limit_or_decommissioned(ValueError("some error")) is False


# ── transcribe_audio ──────────────────────────────────────────────────────────


class TestTranscribeAudio:
    @pytest.mark.asyncio
    async def test_success(self, tmp_path):
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio content")

        svc = _make_service()
        transcription_mock = MagicMock()
        transcription_mock.text = "Hallo Welt"
        svc.client.audio.transcriptions.create = AsyncMock(return_value=transcription_mock)

        result = await svc.transcribe_audio(str(audio_file))
        assert result == "Hallo Welt"

    @pytest.mark.asyncio
    async def test_rate_limit_raises_rate_limit_error(self, tmp_path):
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"data")

        svc = _make_service()
        svc.client.audio.transcriptions.create = AsyncMock(side_effect=_make_rate_limit_error())

        with pytest.raises(RateLimitError):
            await svc.transcribe_audio(str(audio_file))

    @pytest.mark.asyncio
    async def test_generic_exception_raises_transcription_error(self, tmp_path):
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"data")

        svc = _make_service()
        svc.client.audio.transcriptions.create = AsyncMock(side_effect=RuntimeError("network error"))

        with pytest.raises(TranscriptionError):
            await svc.transcribe_audio(str(audio_file))


# ── chat_completion ───────────────────────────────────────────────────────────


class TestChatCompletion:
    @pytest.mark.asyncio
    async def test_success_first_model(self):
        svc = _make_service()
        svc.client.chat.completions.create = AsyncMock(return_value=_chat_response("Response text"))

        result = await svc.chat_completion(
            messages=[{"role": "user", "content": "Hallo"}],
            system_prompt="Du bist ein Assistent.",
        )
        assert result == "Response text"

    @pytest.mark.asyncio
    async def test_fallback_on_rate_limit(self):
        svc = _make_service()
        call_count = 0

        async def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise _make_rate_limit_error()
            return _chat_response("Fallback response")

        svc.client.chat.completions.create = AsyncMock(side_effect=side_effect)

        result = await svc.chat_completion(
            messages=[{"role": "user", "content": "Test"}],
            system_prompt="System.",
            models=["model-a", "model-b"],
        )
        assert result == "Fallback response"

    @pytest.mark.asyncio
    async def test_all_models_exhausted_raises_model_exhausted(self):
        svc = _make_service()
        svc.client.chat.completions.create = AsyncMock(side_effect=_make_rate_limit_error())

        with pytest.raises(ModelExhaustedError):
            await svc.chat_completion(
                messages=[{"role": "user", "content": "Test"}],
                system_prompt="System.",
                models=["model-a", "model-b"],
            )

    @pytest.mark.asyncio
    async def test_non_rate_limit_raises_ai_service_error(self):
        svc = _make_service()
        svc.client.chat.completions.create = AsyncMock(side_effect=RuntimeError("unexpected error"))

        with pytest.raises(AIServiceError):
            await svc.chat_completion(
                messages=[{"role": "user", "content": "Test"}],
                system_prompt="System.",
            )

    @pytest.mark.asyncio
    async def test_with_response_format(self):
        svc = _make_service()
        svc.client.chat.completions.create = AsyncMock(return_value=_chat_response('{"key": "value"}'))

        result = await svc.chat_completion(
            messages=[{"role": "user", "content": "Test"}],
            system_prompt="System.",
            response_format={"type": "json_object"},
        )
        assert result == '{"key": "value"}'

    @pytest.mark.asyncio
    async def test_with_custom_temperature(self):
        svc = _make_service()
        svc.client.chat.completions.create = AsyncMock(return_value=_chat_response("OK"))

        result = await svc.chat_completion(
            messages=[{"role": "user", "content": "Test"}],
            system_prompt="System.",
            temperature=0.7,
        )
        assert result == "OK"

    @pytest.mark.asyncio
    async def test_empty_content_returns_empty_string(self):
        svc = _make_service()
        choice = MagicMock()
        choice.message.content = None
        resp = MagicMock()
        resp.choices = [choice]
        svc.client.chat.completions.create = AsyncMock(return_value=resp)

        result = await svc.chat_completion(
            messages=[{"role": "user", "content": "Test"}],
            system_prompt="System.",
        )
        assert result == ""


# ── json_completion ───────────────────────────────────────────────────────────


class TestJsonCompletion:
    @pytest.mark.asyncio
    async def test_success(self):
        svc = _make_service()
        svc.client.chat.completions.create = AsyncMock(return_value=_chat_response('{"result": "ok"}'))

        data = await svc.json_completion(
            messages=[{"role": "user", "content": "Generate JSON"}],
            system_prompt="Return JSON.",
        )
        assert data == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_invalid_json_raises_report_generation_error(self):
        svc = _make_service()
        svc.client.chat.completions.create = AsyncMock(return_value=_chat_response("not valid json {{"))

        with pytest.raises(ReportGenerationError, match="kein gültiges JSON"):
            await svc.json_completion(
                messages=[{"role": "user", "content": "Generate JSON"}],
                system_prompt="Return JSON.",
            )


# ── generate_structured_report (legacy) ──────────────────────────────────────


class TestGenerateStructuredReport:
    @pytest.mark.asyncio
    async def test_success(self):
        svc = _make_service()
        payload = {
            "patient_pseudonym": "M.S.",
            "symptoms": ["Sprachstörung"],
            "therapy_progress": "Fortschritte beobachtet",
            "prognosis": "Gut",
        }
        import json

        svc.client.chat.completions.create = AsyncMock(return_value=_chat_response(json.dumps(payload)))

        result = await svc.generate_structured_report("Transcript here")
        assert result.patient_pseudonym == "M.S."

    @pytest.mark.asyncio
    async def test_json_decode_error_raises_report_generation_error(self):
        svc = _make_service()
        svc.client.chat.completions.create = AsyncMock(return_value=_chat_response("invalid json"))

        with pytest.raises(ReportGenerationError):
            await svc.generate_structured_report("transcript")

    @pytest.mark.asyncio
    async def test_rate_limit_raises_rate_limit_error(self):
        svc = _make_service()
        svc.client.chat.completions.create = AsyncMock(side_effect=_make_rate_limit_error())

        with pytest.raises(RateLimitError):
            await svc.generate_structured_report("transcript")

    @pytest.mark.asyncio
    async def test_validation_error_raises_report_generation_error(self):
        import json

        svc = _make_service()
        # Missing required fields → pydantic ValueError
        svc.client.chat.completions.create = AsyncMock(
            return_value=_chat_response(json.dumps({"unexpected_field": "x"}))
        )

        with pytest.raises(ReportGenerationError):
            await svc.generate_structured_report("transcript")
