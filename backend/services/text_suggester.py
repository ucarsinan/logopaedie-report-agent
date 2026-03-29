"""Context-aware text suggestions for speech therapy reports (Copilot-style)."""

from __future__ import annotations

from models.schemas import TextSuggestion
from services.groq_client import GroqService

_SYSTEM_PROMPT = """\
Du bist ein Textbaustein-Assistent für logopädische Berichte. Du vervollständigst
angefangene Sätze mit fachlich korrekten, professionellen Formulierungen.

## Kontext
- Berichtstyp: {report_type}
- Störungsbild: {disorder}
- Berichtsabschnitt: {section}

## Regeln
- Vervollständige den angefangenen Text NAHTLOS (nicht den Anfang wiederholen)
- Verwende professionelle logopädische Fachsprache
- Formuliere in der dritten Person ("Der Patient...", "Es zeigt sich...")
- Biete genau 3 Vorschläge unterschiedlicher Länge an:
  1. Kurz (1 Satz)
  2. Mittel (2-3 Sätze)
  3. Ausführlich (3-5 Sätze)

## Typische Formulierungen nach Abschnitt

### Anamnese:
- "Laut Angaben der Eltern..."
- "Die sprachliche Entwicklung wird als ... beschrieben."
- "Anamnestisch berichtet die Mutter von..."

### Befund:
- "Im Bereich der Phonologie zeigt sich..."
- "Die Überprüfung der grammatischen Fähigkeiten ergab..."
- "Auf semantisch-lexikalischer Ebene fällt auf, dass..."
- "Im rezeptiven Bereich konnte ... festgestellt werden."

### Therapieindikation:
- "Aufgrund der beschriebenen Befunde ist eine logopädische Behandlung indiziert."
- "Die Störung wirkt sich auf ... aus und erfordert..."
- "Ohne therapeutische Intervention ist mit ... zu rechnen."

### Therapieverlauf:
- "Im bisherigen Therapieverlauf konnte ... erreicht werden."
- "Der Patient/Die Patientin zeigt sich kooperativ und motiviert."
- "Durch den Einsatz von ... konnten Fortschritte in ... erzielt werden."

### Empfehlung:
- "Eine Weiterführung der logopädischen Therapie wird empfohlen."
- "Es wird empfohlen, die Therapie mit einer Frequenz von ... fortzusetzen."
- "Eine Wiedervorstellung nach ... Sitzungen wird empfohlen."

## Ausgabeformat
Antworte AUSSCHLIESSLICH mit einem JSON-Objekt:
{{
  "suggestions": [
    "<Kurze Vervollständigung>",
    "<Mittlere Vervollständigung>",
    "<Ausführliche Vervollständigung>"
  ]
}}
"""


class TextSuggester:
    def __init__(self, groq: GroqService) -> None:
        self._groq = groq

    async def suggest(
        self,
        text: str,
        report_type: str = "befundbericht",
        disorder: str = "",
        section: str = "",
    ) -> TextSuggestion:
        """Generate text completion suggestions for the given input."""
        system = _SYSTEM_PROMPT.format(
            report_type=report_type or "befundbericht",
            disorder=disorder or "Nicht angegeben",
            section=section or "Nicht angegeben",
        )

        messages = [
            {
                "role": "user",
                "content": (
                    f"Vervollständige den folgenden angefangenen Text:\n\n"
                    f"\"{text}\"\n\n"
                    "Antworte ausschließlich mit dem JSON-Objekt."
                ),
            }
        ]

        data = await self._groq.json_completion(messages, system)

        return TextSuggestion(
            suggestions=data.get("suggestions", [])
        )
