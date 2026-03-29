"""Groq API client for transcription, chat, and report generation."""

from __future__ import annotations

import json
import logging
import os

from groq import AsyncGroq

from models.schemas import MedicalReport

logger = logging.getLogger(__name__)

# ── Model lists (ordered by preference, each has a separate daily limit) ────
# Chat/anamnesis: smaller, faster models — each ~500k TPD on free tier
_CHAT_MODELS = [
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
]

# Report generation: capable models for structured/complex output
_JSON_MODELS = [
    "llama-3.3-70b-versatile",
    "mixtral-8x7b-32768",
    "llama-3.1-8b-instant",
]

# ── Legacy prompt (kept for /process-audio backward compat) ─────────────────
_LEGACY_SYSTEM_PROMPT = (
    "You are an expert speech therapy (Logopädie) assistant. "
    "Extract the patient details from the transcript and format them as a JSON object "
    "matching the requested schema. If information is missing, infer a professional "
    "placeholder or state 'Nicht angegeben'."
)

_LEGACY_SCHEMA = """Return a JSON object with exactly these fields:
- patient_pseudonym (string): A pseudonym for the patient
- symptoms (array of strings): List of observed symptoms or complaints
- therapy_progress (string): Description of the therapy progress
- prognosis (string): Professional prognosis for the patient
"""


def _is_rate_limit(exc: Exception) -> bool:
    msg = str(exc)
    return "429" in msg or "rate_limit" in msg or "Rate limit" in msg


class GroqService:
    def __init__(self) -> None:
        self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

    # ── Audio transcription ──────────────────────────────────────────────
    async def transcribe_audio(self, file_path: str) -> str:
        try:
            with open(file_path, "rb") as f:
                transcription = await self.client.audio.transcriptions.create(
                    file=(os.path.basename(file_path), f.read()),
                    model="whisper-large-v3",
                )
            return transcription.text
        except Exception as e:
            raise RuntimeError(f"Transkription fehlgeschlagen: {e}") from e

    # ── Legacy report generation (for /process-audio) ───────────────────
    async def generate_structured_report(self, transcript: str) -> MedicalReport:
        try:
            response = await self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _LEGACY_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"{_LEGACY_SCHEMA}\n\nTranscript:\n{transcript}",
                    },
                ],
            )
            raw = response.choices[0].message.content
            data = json.loads(raw)
            return MedicalReport(**data)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"LLM hat kein gültiges JSON zurückgegeben: {e}") from e
        except (ValueError, TypeError) as e:
            raise RuntimeError(f"Bericht-Validierung fehlgeschlagen: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Berichtgenerierung fehlgeschlagen: {e}") from e

    # ── Chat completion with model rotation ─────────────────────────────
    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
        response_format: dict | None = None,
        models: list[str] | None = None,
    ) -> str:
        """Send a chat completion request with automatic model fallback on rate limits."""
        model_list = models or _CHAT_MODELS
        last_exc: Exception | None = None

        for model in model_list:
            try:
                kwargs: dict = {
                    "model": model,
                    "messages": [{"role": "system", "content": system_prompt}, *messages],
                }
                if response_format:
                    kwargs["response_format"] = response_format
                response = await self.client.chat.completions.create(**kwargs)
                if model != model_list[0]:
                    logger.info("Model fallback succeeded with: %s", model)
                return response.choices[0].message.content or ""
            except Exception as e:
                if _is_rate_limit(e):
                    logger.warning("Rate limit on %s, trying next model.", model)
                    last_exc = e
                    continue
                raise RuntimeError(f"Chat-Anfrage fehlgeschlagen: {e}") from e

        raise RuntimeError(
            f"Alle Modelle erschöpft. Bitte morgen erneut versuchen. ({last_exc})"
        )

    # ── JSON chat completion with model rotation ─────────────────────────
    async def json_completion(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
        models: list[str] | None = None,
    ) -> dict:
        """Chat completion that returns parsed JSON, with model fallback."""
        raw = await self.chat_completion(
            messages,
            system_prompt,
            response_format={"type": "json_object"},
            models=models or _JSON_MODELS,
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"LLM hat kein gültiges JSON zurückgegeben: {e}") from e
