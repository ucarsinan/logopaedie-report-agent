"""Compare two speech therapy reports and identify changes/progress."""

from __future__ import annotations

from models.schemas import ComparisonItem, ReportComparison
from services.file_processor import extract_text
from services.groq_client import GroqService

_SYSTEM_PROMPT = """\
Du bist ein erfahrener Logopäde/eine erfahrene Logopädin und analysierst
den Therapiefortschritt durch Vergleich zweier logopädischer Berichte.

## Deine Aufgabe
Vergleiche den Erstbefund (oder älteren Bericht) mit dem aktuellen Bericht
und identifiziere Veränderungen in allen relevanten Bereichen.

## Vergleichskategorien
Analysiere mindestens die folgenden Bereiche (soweit aus den Berichten ersichtlich):
- **Phonologie/Phonetik:** Aussprache, Lautinventar, phonologische Prozesse
- **Grammatik/Morphologie:** Satzbildung, Flexion, Satzkomplexität
- **Semantik/Lexikon:** Wortschatz, Wortfindung, Wortbedeutung
- **Pragmatik/Kommunikation:** Gesprächsverhalten, Blickkontakt, Turn-Taking
- **Sprachverständnis:** Rezeptive Fähigkeiten
- **Schriftsprache:** Lesen und Schreiben (falls relevant)
- **Stimme:** Stimmqualität, -umfang, -belastbarkeit (falls relevant)
- **Redefluss:** Flüssigkeit, Stottern, Poltern (falls relevant)
- **Schlucken:** Schluckfunktion, Kostform (falls relevant)
- **Teilhabe:** Auswirkungen auf Alltag, Schule, Beruf

## Ausgabeformat
Antworte AUSSCHLIESSLICH mit einem JSON-Objekt:
{{
  "items": [
    {{
      "category": "<Bereich, z.B. Phonologie>",
      "initial_finding": "<Befund aus dem älteren Bericht>",
      "current_finding": "<Befund aus dem aktuellen Bericht>",
      "change": "<verbessert|unverändert|verschlechtert>",
      "details": "<Detaillierte Beschreibung der Veränderung>"
    }}
  ],
  "overall_progress": "<Zusammenfassende Einschätzung des Gesamtfortschritts>",
  "remaining_issues": ["<Noch bestehende Probleme>"],
  "recommendation": "<Empfehlung: Fortführung/Entlassung mit Begründung>"
}}

## Wichtig
- Vergleiche NUR Informationen, die in BEIDEN Berichten vorhanden sind
- Sei präzise: Beschreibe konkrete Veränderungen, nicht nur "besser/schlechter"
- Die Empfehlung muss §12 SGB V berücksichtigen (ausreichend, zweckmäßig, wirtschaftlich)
- Wenn ein Bereich nur in einem Bericht erwähnt wird, notiere das in "details"
"""


class ReportComparator:
    def __init__(self, groq: GroqService) -> None:
        self._groq = groq

    async def compare(
        self,
        initial_text: str,
        current_text: str,
    ) -> ReportComparison:
        """Compare two report texts and return a structured comparison."""
        messages = [
            {
                "role": "user",
                "content": (
                    "Vergleiche die folgenden beiden logopädischen Berichte:\n\n"
                    "## ERSTBEFUND / ÄLTERER BERICHT:\n"
                    f"{initial_text[:4000]}\n\n"
                    "## AKTUELLER BERICHT:\n"
                    f"{current_text[:4000]}\n\n"
                    "Antworte ausschließlich mit dem JSON-Objekt."
                ),
            }
        ]

        data = await self._groq.json_completion(messages, _SYSTEM_PROMPT)

        return ReportComparison(
            items=[
                ComparisonItem(
                    category=item.get("category", ""),
                    initial_finding=item.get("initial_finding", ""),
                    current_finding=item.get("current_finding", ""),
                    change=item.get("change", "unverändert"),
                    details=item.get("details", ""),
                )
                for item in data.get("items", [])
            ],
            overall_progress=data.get("overall_progress", ""),
            remaining_issues=data.get("remaining_issues", []),
            recommendation=data.get("recommendation", ""),
        )

    async def compare_files(
        self,
        initial_content: bytes,
        initial_filename: str,
        initial_content_type: str,
        current_content: bytes,
        current_filename: str,
        current_content_type: str,
    ) -> ReportComparison:
        """Compare two uploaded files."""
        initial_text = await extract_text(initial_content, initial_filename, initial_content_type)
        current_text = await extract_text(current_content, current_filename, current_content_type)
        return await self.compare(initial_text, current_text)
