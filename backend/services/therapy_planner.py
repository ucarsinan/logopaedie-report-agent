"""Generate ICF-based therapy plans from diagnostic reports."""

from __future__ import annotations

from models.schemas import TherapyGoal, TherapyPhase, TherapyPlan
from services.groq_client import GroqService
from services.session_store import Session

_SYSTEM_PROMPT = """\
Du bist ein erfahrener Logopäde/eine erfahrene Logopädin und erstellst
evidenzbasierte Therapiepläne auf Basis logopädischer Befundberichte.

## Deine Aufgabe
Erstelle einen strukturierten Therapieplan mit ICF-Bezug auf Basis der
vorliegenden Daten (Befundbericht, Anamnese, Diagnose).

## ICF-Klassifikation – Relevante Codes für die Logopädie

### Körperfunktionen (b):
- b110 Funktionen des Bewusstseins
- b117 Funktionen der Intelligenz
- b140 Funktionen der Aufmerksamkeit
- b144 Funktionen des Gedächtnisses
- b167 Mentale Funktionen der Sprache
- b176 Mentale Funktionen, die die Abfolge komplexer Bewegungen betreffen
- b230 Hörfunktionen
- b310 Funktionen der Stimme
- b320 Artikulationsfunktionen
- b330 Funktionen des Redeflusses und Sprechrhythmus
- b340 Alternative stimmliche Äußerungen
- b510 Funktionen der Nahrungsaufnahme (Schlucken)

### Aktivitäten und Partizipation (d):
- d115 Zuhören
- d130 Nachmachen, Nachahmen
- d133 Sprache erwerben
- d134 Zusätzliche Sprache erwerben
- d135 Üben (Rehearsing)
- d310 Kommunizieren als Empfänger gesprochener Mitteilungen
- d315 Kommunizieren als Empfänger nonverbaler Mitteilungen
- d330 Sprechen
- d335 Nonverbale Mitteilungen produzieren
- d350 Konversation
- d355 Diskussion
- d360 Kommunikationsgeräte benutzen
- d570 Auf seine Gesundheit achten
- d820 Schulbildung
- d850 Bezahlte Tätigkeit

## Therapieplan-Struktur

Erstelle den Plan in Phasen (z.B. Aufbauphase, Übungsphase, Transferphase,
Stabilisierungsphase). Jede Phase enthält:
- Konkrete Therapieziele mit ICF-Code-Bezug
- Evidenzbasierte Methoden und Materialien
- Messbare Meilensteine
- Zeitrahmen

## Ausgabeformat
Antworte AUSSCHLIESSLICH mit einem JSON-Objekt:
{{
  "patient_pseudonym": "<Pseudonym>",
  "diagnose_text": "<Kurze Diagnose>",
  "plan_phases": [
    {{
      "phase_name": "<Name der Phase>",
      "duration": "<z.B. 10 Sitzungen>",
      "goals": [
        {{
          "icf_code": "<z.B. b320 Artikulationsfunktionen>",
          "goal_text": "<Konkretes, messbares Therapieziel>",
          "methods": ["<Methode 1>", "<Methode 2>"],
          "milestones": ["<Meilenstein 1>", "<Meilenstein 2>"],
          "timeframe": "<z.B. Sitzung 1-5>"
        }}
      ]
    }}
  ],
  "frequency": "<z.B. 2x pro Woche, 45 Min.>",
  "total_sessions": <Gesamtanzahl>,
  "elternberatung": "<Empfehlungen für Eltern/Angehörige>",
  "haeusliche_uebungen": ["<Übung 1>", "<Übung 2>"]
}}

## Wichtig
- Jedes Ziel muss SMART sein (Spezifisch, Messbar, Attraktiv, Realistisch, Terminiert)
- Methoden müssen evidenzbasiert sein (z.B. P.O.P.T., TOLGS, Patholinguistik, PROMPT, etc.)
- Berücksichtige das Alter und die Lebenssituation des Patienten
- Plane realistisch (orientiere dich an der orientierenden Behandlungsmenge der HeilM-RL)
"""


class TherapyPlanner:
    def __init__(self, groq: GroqService) -> None:
        self._groq = groq

    async def generate_plan(self, session: Session) -> TherapyPlan:
        """Generate a therapy plan from session data and generated report."""
        data = session.collected_data
        report = session.generated_report or {}

        context_parts = [
            f"Berichtstyp: {session.report_type or 'befundbericht'}",
            f"Patient: {data.get('patient_pseudonym', 'Patient')}",
            f"Altersgruppe: {data.get('age_group', 'erwachsen')}",
            f"Indikationsschlüssel: {data.get('indikationsschluessel', 'Nicht angegeben')}",
            f"ICD-10: {', '.join(data.get('icd_10_codes', []))}",
            f"Diagnose: {data.get('diagnose_text', report.get('diagnose', {}).get('diagnose_text', ''))}",
        ]

        # Add report content if available
        if report.get("anamnese"):
            context_parts.append(f"Anamnese: {report['anamnese']}")
        if report.get("befund"):
            context_parts.append(f"Befund: {report['befund']}")
        if report.get("therapieindikation"):
            context_parts.append(f"Therapieindikation: {report['therapieindikation']}")
        if report.get("therapieziele"):
            context_parts.append(f"Therapieziele: {', '.join(report['therapieziele'])}")
        if report.get("empfehlung"):
            context_parts.append(f"Empfehlung: {report['empfehlung']}")

        # Add therapy course info for follow-up plans
        for key in ("therapieinhalte", "fortschritte", "kooperation", "haeusliches_ueben"):
            val = data.get(key)
            if val:
                context_parts.append(f"{key}: {val}")

        context = "\n".join(f"- {p}" for p in context_parts)

        messages = [
            {
                "role": "user",
                "content": (
                    f"Erstelle einen Therapieplan auf Basis folgender Daten:\n\n{context}\n\n"
                    "Antworte ausschließlich mit dem JSON-Objekt."
                ),
            }
        ]

        result = await self._groq.json_completion(messages, _SYSTEM_PROMPT)

        return TherapyPlan(
            patient_pseudonym=result.get("patient_pseudonym", data.get("patient_pseudonym", "Patient")),
            diagnose_text=result.get("diagnose_text", ""),
            plan_phases=[
                TherapyPhase(
                    phase_name=phase.get("phase_name", ""),
                    duration=phase.get("duration", ""),
                    goals=[
                        TherapyGoal(
                            icf_code=g.get("icf_code", ""),
                            goal_text=g.get("goal_text", ""),
                            methods=g.get("methods", []),
                            milestones=g.get("milestones", []),
                            timeframe=g.get("timeframe", ""),
                        )
                        for g in phase.get("goals", [])
                    ],
                )
                for phase in result.get("plan_phases", [])
            ],
            frequency=result.get("frequency", ""),
            total_sessions=result.get("total_sessions", 0),
            elternberatung=result.get("elternberatung", ""),
            haeusliche_uebungen=result.get("haeusliche_uebungen", []),
        )
