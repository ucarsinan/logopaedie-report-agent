"""Anamnesis conversation engine for speech therapy report generation.

Guides the therapist through a structured interview to collect all
information needed for generating a professional report.
"""

from __future__ import annotations

from models.schemas import ChatMessage
from services.groq_client import GroqService
from services.session_store import Session

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
- Sprich den/die Therapeut:in immer mit "Sie" an
- Überspringe Phasen, die für den gewählten Berichtstyp nicht relevant sind
  (z.B. Phase 5 bei Befundbericht)
- Wenn der/die Therapeut:in Informationen aus mehreren Phasen gleichzeitig gibt,
  erkenne das und überspringe bereits beantwortete Fragen
- Frage nie nach Feldern, die bereits erfasst sind
- Gib am Ende jeder Nachricht KEINE JSON-Ausgabe – antworte rein im Gesprächston

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


_REQUIRED_FIELDS: dict[str, list[str]] = {
    "befundbericht": [
        "patient_pseudonym", "age_group", "indikationsschluessel",
        "anamnese_persoenlich", "diagnose_text",
    ],
    "therapiebericht_kurz": [
        "patient_pseudonym", "age_group", "indikationsschluessel", "therapieziele",
    ],
    "therapiebericht_lang": [
        "patient_pseudonym", "age_group", "indikationsschluessel",
        "anamnese_persoenlich", "diagnose_text", "therapieinhalte", "fortschritte",
    ],
    "abschlussbericht": [
        "patient_pseudonym", "age_group", "indikationsschluessel",
        "therapieinhalte", "anzahl_sitzungen", "fortschritte", "kooperation",
    ],
}


class AnamnesisEngine:
    def __init__(self, groq: GroqService) -> None:
        self._groq = groq

    def _compute_missing_fields(self, session: Session) -> list[str]:
        """Return required fields not yet collected for the current report type."""
        report_type = session.collected_data.get("report_type")
        if not report_type:
            return []
        required = _REQUIRED_FIELDS.get(report_type, [])
        return [f for f in required if not session.collected_data.get(f)]

    async def process_message(self, session: Session, user_message: str) -> str:
        """Process a user message and return the assistant's response."""
        # Add user message to history
        session.chat_history.append(ChatMessage(role="user", content=user_message))

        # Build context for the conversation prompt
        report_type = session.collected_data.get("report_type", "Noch nicht festgelegt")
        age_group = session.collected_data.get("age_group", "Noch nicht festgelegt")
        disorder = session.collected_data.get("indikationsschluessel", "Noch nicht festgelegt")
        collected = list(session.collected_data.get("collected_fields", []))
        missing = self._compute_missing_fields(session)

        system = _ANAMNESIS_SYSTEM_PROMPT.format(
            report_type=report_type,
            age_group=age_group,
            disorder=disorder,
            collected_fields=", ".join(collected) if collected else "Keine",
            missing_fields=", ".join(missing) if missing else "Alle Pflichtfelder erfasst",
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
        """Generate the initial greeting message to start the anamnesis."""
        system = _ANAMNESIS_SYSTEM_PROMPT.format(
            report_type="Noch nicht festgelegt",
            age_group="Noch nicht festgelegt",
            disorder="Noch nicht festgelegt",
            collected_fields="Keine",
            missing_fields="Berichtstyp zuerst klären",
        )

        messages = [
            {
                "role": "user",
                "content": "Bitte begrüße mich und frage, welchen Berichtstyp ich erstellen möchte.",
            }
        ]
        response_text = await self._groq.chat_completion(messages, system)

        session.chat_history.append(ChatMessage(role="assistant", content=response_text))
        return response_text

    async def get_contextual_greeting(self, session: Session) -> str:
        """Generate a contextual greeting for a returning patient in a new session."""
        # Check for patient name (pseudonym first, then fallback to patient_name)
        patient_name = session.collected_data.get("patient_pseudonym") or session.collected_data.get("patient_name")

        # If no patient name found, fall back to initial greeting
        if not patient_name:
            return await self.get_initial_greeting(session)

        # Generate contextual greeting for returning patient
        system = _ANAMNESIS_SYSTEM_PROMPT.format(
            report_type="Noch nicht festgelegt",
            age_group="Noch nicht festgelegt",
            disorder="Noch nicht festgelegt",
            collected_fields="Keine",
            missing_fields="Berichtstyp zuerst klären",
        )

        messages = [
            {
                "role": "user",
                "content": f"Bitte begrüße mich für eine neue Sitzung mit {patient_name} und frage, welchen Berichtstyp ich diesmal erstellen möchte.",
            }
        ]
        response_text = await self._groq.chat_completion(messages, system)

        session.chat_history.append(ChatMessage(role="assistant", content=response_text))
        return response_text

    async def _extract_data(self, session: Session) -> None:
        """Extract structured data from the conversation so far."""
        messages = [{"role": m.role, "content": m.content} for m in session.chat_history]
        extraction_messages = [
            {
                "role": "user",
                "content": "Gespräch:\n"
                + "\n".join(f"{m['role']}: {m['content']}" for m in messages),
            }
        ]

        try:
            data = await self._groq.json_completion(extraction_messages, _EXTRACTION_PROMPT)

            # Update session with extracted data
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
                # Merge non-null values into collected_data
                for key, value in data["data"].items():
                    if value is not None and value != [] and value != "":
                        session.collected_data[key] = value

        except RuntimeError:
            # Extraction failed – not critical, conversation continues
            pass
