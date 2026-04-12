"""Generate SOAP notes from session or report data via Groq."""

import json
import logging

from services.groq_client import GroqService

logger = logging.getLogger(__name__)

_SOAP_SYSTEM_PROMPT = """Du bist ein erfahrener Logopäde und erstellst strukturierte SOAP-Notizen.

SOAP steht für:
- **S (Subjektiv):** Subjektive Angaben des Patienten/der Eltern, Beschwerden, Eigenwahrnehmung, Anamnese-Informationen
- **O (Objektiv):** Objektive Befunde aus Tests, Beobachtungen, messbare Ergebnisse, Diagnostik
- **A (Assessment):** Klinische Bewertung, Interpretation der Befunde, Diagnose, Einschätzung des Schweregrades
- **P (Plan):** Therapieplan, konkrete Ziele, Methoden, Frequenz, nächste Schritte, Empfehlungen

Erstelle aus den gegebenen Daten eine präzise, fachlich korrekte SOAP-Notiz auf Deutsch.
Verwende Fachterminologie der Logopädie. Sei konkret und vermende keine Floskeln.

Antworte AUSSCHLIESSLICH im folgenden JSON-Format:
{
  "subjective": "...",
  "objective": "...",
  "assessment": "...",
  "plan": "..."
}
"""


class SOAPGenerator:
    def __init__(self, groq: GroqService) -> None:
        self._groq = groq

    async def generate_from_data(
        self,
        collected_data: dict,
        report: dict | None = None,
    ) -> dict:
        """Generate a SOAP note from session collected data and optional report."""
        context_parts = []

        if collected_data:
            context_parts.append("Erhobene Anamnese-Daten:")
            for key, value in collected_data.items():
                if key.startswith("_") or key in ("greeting",):
                    continue
                if isinstance(value, list):
                    context_parts.append(f"- {key}: {', '.join(str(v) for v in value)}")
                elif value:
                    context_parts.append(f"- {key}: {value}")

        if report:
            context_parts.append("\nGenerierter Bericht:")
            for key, value in report.items():
                if key.startswith("_") or key in ("report_type", "patient", "diagnose"):
                    continue
                if isinstance(value, list):
                    context_parts.append(f"- {key}: {', '.join(str(v) for v in value)}")
                elif value:
                    context_parts.append(f"- {key}: {value}")

            patient = report.get("patient", {})
            if patient:
                context_parts.append(f"\nPatient: {patient.get('pseudonym', 'Unbekannt')}, "
                                     f"Alter: {patient.get('age_group', 'k.A.')}")

            diagnose = report.get("diagnose", {})
            if diagnose:
                context_parts.append(f"Diagnose: {diagnose.get('diagnose_text', 'k.A.')}")
                if diagnose.get("icd_10_codes"):
                    context_parts.append(f"ICD-10: {', '.join(diagnose['icd_10_codes'])}")

        context = "\n".join(context_parts)

        messages = [{"role": "user", "content": context}]
        result = await self._groq.json_completion(messages, _SOAP_SYSTEM_PROMPT)

        if isinstance(result, str):
            result = json.loads(result)

        return {
            "subjective": result.get("subjective", ""),
            "objective": result.get("objective", ""),
            "assessment": result.get("assessment", ""),
            "plan": result.get("plan", ""),
        }
