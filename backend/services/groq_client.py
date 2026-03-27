import json
import os

from groq import AsyncGroq

from backend.models.schemas import MedicalReport

_SYSTEM_PROMPT = (
    "You are an expert speech therapy (Logopädie) assistant. "
    "Extract the patient details from the transcript and format them as a JSON object "
    "matching the requested schema. If information is missing, infer a professional "
    "placeholder or state 'Nicht angegeben'."
)

_SCHEMA_DESCRIPTION = """Return a JSON object with exactly these fields:
- patient_pseudonym (string): A pseudonym for the patient
- symptoms (array of strings): List of observed symptoms or complaints
- therapy_progress (string): Description of the therapy progress
- prognosis (string): Professional prognosis for the patient
"""


class GroqService:
    def __init__(self) -> None:
        self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

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

    async def generate_structured_report(self, transcript: str) -> MedicalReport:
        try:
            response = await self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"{_SCHEMA_DESCRIPTION}\n\nTranscript:\n{transcript}"
                        ),
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
