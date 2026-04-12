"""Anamnesis conversation engine for speech therapy report generation.

Guides the therapist through a structured interview to collect all
information needed for generating a professional report.
"""

from __future__ import annotations

import logging

from models.schemas import ChatMessage
from services.groq_client import GroqService
from services.session_store import Session

logger = logging.getLogger(__name__)

_ANAMNESIS_SYSTEM_PROMPT = """\
Du bist ein logopädischer Dokumentationsassistent. Du führst strukturierte
Anamnesegespräche auf Deutsch und sammelst die nötigen Informationen für Berichte.

## Kommunikationsstil
- Sachlich, direkt, respektvoll. Keine Floskeln, keine Einleitungssätze.
- Bestätige kurz was du verstanden hast (1 Satz), dann stelle genau eine Frage.
- Bei unklaren Antworten: konkret nachfragen, nicht interpretieren.
- Keine Füllwörter ("Natürlich!", "Sehr gerne!", "Das ist wichtig!").
- Maximal 3 Sätze pro Antwort: Bestätigung + 1 Frage.
- Genau eine Frage pro Antwort, ohne Ausnahme.

## Deine Aufgabe
Sammle die nötigen Informationen für den gewünschten Berichtstyp.
Orientiere dich an den fehlenden Pflichtfeldern (siehe Aktueller Stand).

## Gesprächsphasen

### Phase 1: Begrüßung & Berichtstyp (phase: "report_type")
Begrüße den/die Therapeut:in und frage, welchen Berichtstyp er/sie erstellen möchte:
- **Befundbericht** – Erstbefund nach Diagnostik
- **Therapiebericht (kurz)** – Verordnungsbericht mit Empfehlungen (Anhang A)
- **Therapiebericht (lang)** – Ausführlicher Bericht auf besondere Anforderung (Anhang C)
- **Abschlussbericht** – Abschluss einer Verordnungsreihe

Wenn der/die Therapeut:in "Sonstiges" oder einen unbekannten Berichtstyp nennt,
frage freundlich nach: "Was für einen Bericht benötigen Sie? Beschreiben Sie kurz
den Zweck oder die Zielgruppe, damit ich den Prozess optimal anpassen kann."
Verbleibe in der "report_type"-Phase und setze "report_type" auf null, bis der
Typ geklärt ist.

### Phase 2: Patienteninformation (phase: "patient_info")
Frage nach:
- Altersgruppe: Kind, Jugendliche/r oder Erwachsene/r
- Geschlecht (optional)
- Pseudonym oder Initialen für den Bericht

### Phase 3: Störungsbild & Diagnose (phase: "disorder")
Frage nach dem Störungsbild und schlage passende Klassifikationen vor:
- **Sprachstörungen:** SP1 (Sprachentwicklungsstörung), SP2 (auditive Wahrnehmung),
  SP3 (Artikulation/Dyslalie), SP4 (bei Schwerhörigkeit/Taubheit),
  SP5 (Aphasie/Dysphasie), SP6 (Dysarthrie/Sprechapraxie)
- **Stimmstörungen:** ST1 (organisch), ST2 (funktionell)
- **Schluckstörungen:** SC1 (neurologisch bedingte Dysphagie)
- **Redeflussstörungen:** RE1 (Stottern), RE2 (Poltern)
- **Orofazial:** OFD (Myofunktionelle Störung)
Frage auch nach dem ICD-10-Code, falls bekannt. Schlage passende Codes vor:
- F80.x für Sprachentwicklungsstörungen
- R47.x für Sprech-/Sprachstörungen
- R49.x für Stimmstörungen
- R13.x für Schluckstörungen
- F98.5/F98.6 für Redeflussstörungen

### Phase 4: Anamnese (phase: "anamnesis")
Passe die Fragen an das Störungsbild und die Altersgruppe an:

**Bei Kindern (SP1, SP2, SP3, OFD):**
- Schwangerschaft und Geburtsverlauf
- Motorische Entwicklung (Krabbeln, Laufen)
- Sprachentwicklung: Lallen, erste Wörter, erste Sätze, Sprachverständnis
- Hörvermögen, HNO-Befunde, Paukenergüsse
- Familiäre Sprachauffälligkeiten
- Mehrsprachigkeit (welche Sprachen, Verteilung)
- Kindergarten/Schule, sozial-emotionale Entwicklung

**Bei Erwachsenen (SP5, SP6, ST1, ST2, SC1):**
- Symptombeginn und Ursache (Schlaganfall, OP, Trauma, etc.)
- Auswirkung auf Alltag und Beruf
- Bisherige Behandlungen und deren Ergebnisse
- Aktuelle Medikation

**Bei Stimmstörungen (ST1, ST2):**
- Berufliche Stimmbelastung (Lehrer, Sänger, etc.)
- Stimmhygiene-Gewohnheiten
- HNO-Befund (Stimmlippenbefund)
- Reflux, Allergien, Rauchen

**Bei Dysphagie (SC1):**
- Grunderkrankung (Schlaganfall, Parkinson, ALS, etc.)
- Aktuelle Kostform und Flüssigkeitskonsistenz
- Aspirationszeichen (Husten beim Essen/Trinken)
- FEES- oder Videofluoroskopie-Befund falls vorhanden

### Phase 5: Therapieverlauf (phase: "goals") – nur für Verlaufs-/Abschlussberichte
- Bisherige Therapieinhalte und -methoden
- Anzahl der bisherigen Sitzungen
- Fortschritte und Veränderungen seit Therapiebeginn
- Aktuelle Therapieziele
- Vergleich Anfangs- und aktueller Befund
- Kooperation und Mitarbeit des Patienten / der Eltern
- Häusliches Üben

### Phase 6: Zusammenfassung (phase: "summary")
Fasse alle gesammelten Informationen zusammen und bitte um Bestätigung
oder Korrekturen. Frage, ob noch etwas ergänzt werden soll.

## Wichtige Regeln
- **NIEMALS interne Feldnamen oder technische Bezeichner in Antworten zeigen.**
  Verboten sind u.a.: `age_group`, `report_type`, `patient_pseudonym`,
  `indikationsschluessel`, `diagnose_text`, `anamnese_persoenlich`, `icd_10_codes`,
  `collected_fields`, `phase`, snake_case-Bezeichner, JSON-Schlüssel, Code-Backticks.
  Verwende ausschließlich natürliche deutsche Begriffe (z. B. "Altersgruppe",
  "Berichtstyp", "Pseudonym", "Indikationsschlüssel", "Diagnose").
- Sprich den/die Therapeut:in immer mit "Sie" an
- Überspringe Phasen, die für den gewählten Berichtstyp nicht relevant sind
  (z.B. Phase 5 bei Befundbericht)
- Wenn der/die Therapeut:in Informationen aus mehreren Phasen gleichzeitig gibt,
  erkenne das und überspringe bereits beantwortete Fragen
- Frage nie nach Feldern, die bereits erfasst sind
- Gib am Ende jeder Nachricht KEINE JSON-Ausgabe – antworte rein im Gesprächston
- Erfinde NIEMALS Informationen, Namen, Diagnosen oder Befunde.
- Wenn du etwas nicht weißt: frage nach. Niemals raten oder interpolieren.

## Vorhandene Unterlagen
{materials_context}

## Aktueller Stand
Berichtstyp: {report_type}
Altersgruppe: {age_group}
Störungsbild: {disorder}
Bereits erfasste Felder: {collected_fields}
Fehlende Pflichtfelder für diesen Berichtstyp: {missing_fields}
"""

_EXTRACTION_PROMPT = """\
Analysiere das folgende Gespräch zwischen einem logopädischen Assistenten und
einem/einer Therapeut:in. Extrahiere alle bisher genannten Informationen als
strukturiertes JSON.

Antworte AUSSCHLIESSLICH mit einem JSON-Objekt mit diesen Feldern:
{{
  "phase": "<aktuelle Phase: report_type|patient_info|disorder|anamnesis|goals|summary>",
  "is_complete": <true wenn Phase 'summary' erreicht und bestätigt, sonst false>,
  "report_type": "<befundbericht|therapiebericht_kurz|therapiebericht_lang|abschlussbericht|null>",
  "collected_fields": ["<liste der bereits erfassten felder>"],
  "data": {{
    "patient_pseudonym": "<string oder null>",
    "age_group": "<kind|jugendlich|erwachsen|null>",
    "gender": "<string oder null>",
    "indikationsschluessel": "<z.B. SP1, ST2, SC1 oder null>",
    "icd_10_codes": ["<liste der codes>"],
    "diagnose_text": "<Diagnosetext oder null>",
    "anamnese_persoenlich": "<Persönliche Anamnese oder null>",
    "anamnese_familie": "<Familienanamnese oder null>",
    "sprachentwicklung": "<bei Kindern: Sprachentwicklung oder null>",
    "motorische_entwicklung": "<bei Kindern: motorische Entwicklung oder null>",
    "hoervermögen": "<Hörbefunde oder null>",
    "mehrsprachigkeit": "<Mehrsprachigkeitsinfo oder null>",
    "symptombeginn": "<Symptombeginn oder null>",
    "ursache": "<Ursache der Störung oder null>",
    "auswirkung_alltag": "<Auswirkung auf Alltag oder null>",
    "bisherige_behandlung": "<bisherige Behandlungen oder null>",
    "stimmbelastung": "<bei Stimmstörungen oder null>",
    "hno_befund": "<HNO-Befund oder null>",
    "kostform": "<bei Dysphagie: Kostform oder null>",
    "aspirationszeichen": "<bei Dysphagie oder null>",
    "therapieinhalte": "<bisherige Therapieinhalte oder null>",
    "anzahl_sitzungen": "<Anzahl Sitzungen oder null>",
    "fortschritte": "<Fortschritte oder null>",
    "therapieziele": ["<aktuelle Therapieziele>"],
    "kooperation": "<Kooperation Patient/Eltern oder null>",
    "haeusliches_ueben": "<Häusliches Üben oder null>",
    "zusaetzliche_infos": "<weitere relevante Infos oder null>"
  }}
}}

Setze Felder auf null wenn sie im Gespräch nicht erwähnt wurden.
Erfinde KEINE Informationen – extrahiere nur was tatsächlich gesagt wurde.
"""


_QUICK_INPUT_SYSTEM_PROMPT = """Du bist ein effizienter Assistent für Logopäden.

AUFGABE:
Beim ERSTEN Nutzer-Turn: Extrahiere alle Angaben aus dem Freitext. Dann prüfe welche Pflichtfelder für den gewählten Berichtstyp ({report_type}) noch fehlen.
Bei FOLGE-Turns: Die Logopädin hat eine Rückfrage beantwortet. Prüfe erneut die fehlenden Felder.

VERHALTEN:
- Frage immer nach genau EINEM fehlenden Pflichtfeld.
- Formuliere die Frage einzeilig, direkt, ohne Begrüßung oder Smalltalk.
- Wenn alle Pflichtfelder vollständig sind: Antworte exakt mit dem Satz "COMPLETE"
- Erfinde KEINE Informationen. Wenn Daten fehlen: frage danach.

BEISPIELE für gute Fragen:
- "Wie lautet das Geburtsdatum des Patienten?"
- "Welchen Indikationsschlüssel verwenden Sie?"
- "Wie viele Sitzungen wurden insgesamt durchgeführt?"

Fehlende Felder: {missing_fields}"""

_THERAPY_PLAN_SYSTEM_PROMPT = """\
Du bist ein logopädischer Dokumentationsassistent. Du sammelst kurz die nötigen
Informationen für einen ICF-basierten Therapieplan.

## Kommunikationsstil
- Sachlich, direkt, respektvoll. Keine Floskeln.
- Bestätige kurz was du verstanden hast (1 Satz), dann stelle genau eine Frage.
- Maximal 2 Sätze pro Antwort. Genau eine Frage, ohne Ausnahme.
- **NIEMALS interne Feldnamen oder technische Bezeichner zeigen** (z. B. `age_group`,
  `patient_pseudonym`, `diagnose_text`, snake_case, JSON-Schlüssel). Nutze nur
  natürliche deutsche Begriffe wie "Altersgruppe", "Pseudonym", "Diagnose".

## Deine Aufgabe
Sammle diese 4 Informationen (in dieser Reihenfolge, falls noch nicht vorhanden):
1. **Pseudonym/Initialen** des Patienten
2. **Altersgruppe**: Kind (bis 12), Jugendliche/r (13-17) oder Erwachsene/r
3. **Diagnose/Störungsbild** (z.B. Aphasie, Sprachentwicklungsstörung, Stottern)
4. **Hauptproblematik/aktuelle Situation** (kurze Beschreibung des aktuellen Standes)

Sobald alle 4 Felder gesammelt sind, fasse kurz zusammen und erkläre,
dass der Therapieplan jetzt generiert werden kann.

## Aktueller Stand
Bereits erfasst: {collected_fields}
Noch fehlend: {missing_fields}
- Erfinde NIEMALS Informationen. Wenn ein Feld unklar ist: frage konkret nach.
"""

_THERAPY_PLAN_EXTRACTION_PROMPT = """\
Analysiere das folgende Gespräch und extrahiere die Informationen für den Therapieplan.

Antworte AUSSCHLIESSLICH mit einem JSON-Objekt:
{{
  "is_complete": <true wenn alle 4 Felder vorhanden, sonst false>,
  "collected_fields": ["<liste der erfassten felder>"],
  "data": {{
    "patient_pseudonym": "<string oder null>",
    "age_group": "<kind|jugendlich|erwachsen|null>",
    "diagnose_text": "<Diagnose/Störungsbild oder null>",
    "hauptproblematik": "<aktuelle Situation/Hauptproblematik oder null>"
  }}
}}

Setze Felder auf null wenn nicht im Gespräch erwähnt.
Erfinde KEINE Informationen.
"""

_REQUIRED_FIELDS_THERAPY_PLAN = ["patient_pseudonym", "age_group", "diagnose_text", "hauptproblematik"]

_REQUIRED_FIELDS: dict[str, list[str]] = {
    "befundbericht": [
        "patient_pseudonym",
        "age_group",
        "indikationsschluessel",
        "anamnese_persoenlich",
        "diagnose_text",
    ],
    "therapiebericht_kurz": [
        "patient_pseudonym",
        "age_group",
        "indikationsschluessel",
        "therapieziele",
    ],
    "therapiebericht_lang": [
        "patient_pseudonym",
        "age_group",
        "indikationsschluessel",
        "anamnese_persoenlich",
        "diagnose_text",
        "therapieinhalte",
        "fortschritte",
    ],
    "abschlussbericht": [
        "patient_pseudonym",
        "age_group",
        "indikationsschluessel",
        "therapieinhalte",
        "anzahl_sitzungen",
        "fortschritte",
        "kooperation",
    ],
}

_VALID_AGE_GROUPS = {"kind", "jugendlich", "erwachsen"}
_VALID_REPORT_TYPES = {"befundbericht", "therapiebericht_kurz", "therapiebericht_lang", "abschlussbericht"}
_VALID_PHASES = {"greeting", "report_type", "patient_info", "disorder", "anamnesis", "goals", "summary"}
_VALID_INDIKATIONSSCHLUESSEL = {"SP1", "SP2", "SP3", "SP4", "SP5", "SP6", "ST1", "ST2", "SC1", "RE1", "RE2", "OFD"}


def _validate_extracted_data(data: dict) -> dict:
    """Remove hallucinated enum values before storing in session."""
    cleaned = {}
    for key, value in data.items():
        if value is None or value == "" or value == []:
            continue
        if key == "age_group" and value not in _VALID_AGE_GROUPS:
            continue
        if key == "report_type" and value not in _VALID_REPORT_TYPES:
            continue
        if key == "phase" and value not in _VALID_PHASES:
            continue
        if key == "indikationsschluessel" and value not in _VALID_INDIKATIONSSCHLUESSEL:
            continue
        cleaned[key] = value
    return cleaned


class AnamnesisEngine:
    def __init__(self, groq: GroqService) -> None:
        self._groq = groq

    def _format_materials_context(self, session: Session) -> str:
        """Return a formatted string of uploaded material texts for the system prompt."""
        if not session.materials_consent or not session.materials:
            return "Keine Unterlagen vorhanden."
        parts = []
        for mat in session.materials:
            snippet = mat.extracted_text[:1500].strip()
            parts.append(f"**{mat.filename}** ({mat.material_type}):\n{snippet}")
        return "\n\n".join(parts)

    def _compute_missing_fields(self, session: Session) -> list[str]:
        """Return required fields not yet collected for the current report type."""
        if session.therapy_plan_mode:
            return [f for f in _REQUIRED_FIELDS_THERAPY_PLAN if not session.collected_data.get(f)]
        report_type = session.collected_data.get("report_type")
        if not report_type:
            return []
        required = _REQUIRED_FIELDS.get(report_type, [])
        return [f for f in required if not session.collected_data.get(f)]

    async def process_message(self, session: Session, user_message: str, mode: str = "guided") -> str:
        """Process a user message and return the assistant's response."""
        # Add user message to history
        session.chat_history.append(ChatMessage(role="user", content=user_message))

        collected = list(session.collected_data.get("collected_fields", []))
        missing = self._compute_missing_fields(session)

        if session.therapy_plan_mode:
            system = _THERAPY_PLAN_SYSTEM_PROMPT.format(
                collected_fields=", ".join(collected) if collected else "Keine",
                missing_fields=", ".join(missing) if missing else "Alle Felder erfasst",
            )
        elif mode == "quick_input":
            report_type = session.collected_data.get("report_type", "unbekannt")
            system = _QUICK_INPUT_SYSTEM_PROMPT.format(
                report_type=report_type,
                missing_fields=", ".join(missing) if missing else "keine",
            )
        else:
            report_type = session.collected_data.get("report_type", "Noch nicht festgelegt")
            age_group = session.collected_data.get("age_group", "Noch nicht festgelegt")
            disorder = session.collected_data.get("indikationsschluessel", "Noch nicht festgelegt")
            system = _ANAMNESIS_SYSTEM_PROMPT.format(
                report_type=report_type,
                age_group=age_group,
                disorder=disorder,
                collected_fields=", ".join(collected) if collected else "Keine",
                missing_fields=", ".join(missing) if missing else "Alle Pflichtfelder erfasst",
                materials_context=self._format_materials_context(session),
            )

        # Get conversational response
        messages = [{"role": m.role, "content": m.content} for m in session.chat_history]
        response_text = await self._groq.chat_completion(messages, system)

        # Add assistant response to history
        session.chat_history.append(ChatMessage(role="assistant", content=response_text))

        # Extract structured data from the conversation
        await self._extract_data(session)

        return response_text

    async def get_initial_greeting(self, session: Session) -> str:
        """Return a static greeting — no LLM call to prevent hallucination."""
        if session.therapy_plan_mode:
            greeting = (
                "Guten Tag! Ich helfe Ihnen beim Erstellen eines Therapieplans. "
                "Bitte nennen Sie zunächst das Pseudonym des Patienten."
            )
        else:
            greeting = (
                "Guten Tag! Für welchen Berichtstyp benötigen Sie Unterstützung?\n\n"
                "– Befundbericht\n– Therapiebericht kurz\n– Therapiebericht lang\n– Abschlussbericht"
            )
        session.chat_history.append(ChatMessage(role="assistant", content=greeting))
        return greeting

    async def get_contextual_greeting(self, session: Session) -> str:
        """Return a static contextual greeting — no LLM call."""
        patient_name = session.collected_data.get("patient_pseudonym") or session.collected_data.get("patient_name")
        if patient_name:
            greeting = f"Willkommen zurück! Wir setzen die Dokumentation für {patient_name} fort. Um was für einen Bericht handelt es sich?"
        else:
            greeting = "Willkommen zurück! Um was für einen Bericht handelt es sich?"
        session.chat_history.append(ChatMessage(role="assistant", content=greeting))
        return greeting

    async def _extract_data(self, session: Session) -> None:
        """Extract structured data from the conversation so far."""
        messages = [{"role": m.role, "content": m.content} for m in session.chat_history]
        extraction_messages = [
            {
                "role": "user",
                "content": "Gespräch:\n" + "\n".join(f"{m['role']}: {m['content']}" for m in messages),
            }
        ]

        try:
            if session.therapy_plan_mode:
                data = await self._groq.json_completion(extraction_messages, _THERAPY_PLAN_EXTRACTION_PROMPT)
                if data.get("collected_fields"):
                    session.collected_data["collected_fields"] = data["collected_fields"]
                if data.get("is_complete"):
                    session.status = "materials"
                if data.get("data"):
                    validated = _validate_extracted_data(data["data"])
                    session.collected_data.update(validated)
            else:
                data = await self._groq.json_completion(extraction_messages, _EXTRACTION_PROMPT)

                if data.get("report_type"):
                    session.report_type = data["report_type"]
                    session.collected_data["report_type"] = data["report_type"]

                if data.get("phase"):
                    session.collected_data["current_phase"] = data["phase"]

                if data.get("collected_fields"):
                    session.collected_data["collected_fields"] = data["collected_fields"]

                if data.get("is_complete"):
                    session.status = "materials"

                if data.get("data"):
                    validated = _validate_extracted_data(data["data"])
                    session.collected_data.update(validated)

        except Exception as e:
            logger.warning("_extract_data failed: %s", e)
