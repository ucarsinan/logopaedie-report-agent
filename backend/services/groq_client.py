"""Groq API client for transcription, chat, and report generation."""

from __future__ import annotations

import json
import os

from groq import AsyncGroq

from models.schemas import MedicalReport

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


class GroqService:
    def __init__(self) -> None:
        self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

    # ── Audio transcription (unchanged) ─────────────────────────────────
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

    # ── Chat completion (for anamnesis conversation) ────────────────────
    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
        response_format: dict | None = None,
        model: str = "llama-3.1-8b-instant",
    ) -> str:
        """Send a chat completion request and return the assistant message content."""
        try:
            kwargs: dict = {
                "model": model,
                "messages": [{"role": "system", "content": system_prompt}, *messages],
            }
            if response_format:
                kwargs["response_format"] = response_format
            response = await self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"Chat-Anfrage fehlgeschlagen: {e}") from e

    # ── JSON chat completion (for structured extraction) ────────────────
    async def json_completion(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
        model: str = "llama-3.3-70b-versatile",
    ) -> dict:
        """Chat completion that returns parsed JSON."""
        raw = await self.chat_completion(
            messages, system_prompt, response_format={"type": "json_object"}, model=model
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"LLM hat kein gültiges JSON zurückgegeben: {e}") from e
