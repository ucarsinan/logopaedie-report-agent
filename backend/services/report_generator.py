"""Generate structured speech therapy reports based on anamnesis data."""

from __future__ import annotations

from backend.models.schemas import (
    Abschlussbericht,
    Befundbericht,
    Diagnose,
    PatientInfo,
    ReportUnion,
    TherapieberichtKurz,
    TherapieberichtLang,
)
from backend.services.groq_client import GroqService
from backend.services.session_store import Session

# ── Base prompt shared by all report types ──────────────────────────────────
_BASE_PROMPT = """\
Du bist ein erfahrener logopädischer Fachassistent für die Berichterstellung.
Erstelle auf Basis der gesammelten Anamnese-Daten einen professionellen
logopädischen Bericht auf Deutsch.

## Allgemeine Anforderungen
- Verwende professionelle logopädische Fachsprache
- Schreibe in der dritten Person (z.B. "Der Patient zeigt...")
- Formuliere sachlich und präzise
- Beachte §12 SGB V: Heilmittel müssen ausreichend, zweckmäßig und wirtschaftlich sein
- Verwende Pseudonyme statt echter Patientennamen
- Bei fehlenden Informationen schreibe "Nicht erhoben" oder "Keine Angaben"
- Orientiere dich an ICF-Klassifikation wo möglich

## Gesammelte Anamnese-Daten
{anamnesis_data}

## Hochgeladene Materialien (falls vorhanden)
{materials}
"""

# ── Report-type-specific prompts ────────────────────────────────────────────
_BEFUNDBERICHT_PROMPT = _BASE_PROMPT + """
## Berichtstyp: Befundbericht (Erstbefund nach Diagnostik)

Erstelle einen Befundbericht mit exakt dieser JSON-Struktur:
{{
  "anamnese": "<Ausführliche persönliche und Familienanamnese. Bei Kindern: Schwangerschaft, Geburt, motorische Entwicklung, Sprachentwicklung, Hörvermögen, familiäre Vorbelastung, Mehrsprachigkeit. Bei Erwachsenen: Symptombeginn, Ursache, bisherige Behandlung, Auswirkung auf Alltag.>",
  "befund": "<Detaillierte diagnostische Befunde auf allen relevanten linguistischen Ebenen: Phonetik/Phonologie, Semantik/Lexikon, Morphologie/Syntax, Pragmatik/Kommunikation. Bei Stimmstörungen: Stimmklang, Stimmumfang, Tonus, Atmung. Bei Dysphagie: Schluckphasen, Aspirationsrisiko, Kostform.>",
  "diagnose_text": "<Zusammenfassende Diagnose mit Bezug auf ICD-10 und Indikationsschlüssel>",
  "therapieindikation": "<Begründung der Therapienotwendigkeit und -dringlichkeit. Auswirkungen der Störung auf Kommunikation, Teilhabe, Schullaufbahn (bei Kindern) oder Beruf (bei Erwachsenen).>",
  "therapieziele": ["<Ziel 1>", "<Ziel 2>", "<...weitere Ziele>"],
  "empfehlung": "<Empfehlung bezüglich Therapiefrequenz, -dauer und weiterem Vorgehen>"
}}
"""

_THERAPIEBERICHT_KURZ_PROMPT = _BASE_PROMPT + """
## Berichtstyp: Therapiebericht kurz (Verordnungsbericht, Anhang A zu Anlage 1)

Dies ist ein kurzer Verordnungsbericht mit Empfehlungen gemäß dem offiziellen
Formularvordruck. Erstelle den Bericht mit exakt dieser JSON-Struktur:
{{
  "empfehlungen": "<Kurze, prägnante Empfehlungen zum weiteren therapeutischen Vorgehen. Beinhaltet: Einschätzung ob Fortführung der Therapie empfohlen wird, empfohlene Therapiefrequenz, ggf. Änderung des Therapieansatzes, Hinweise für den verordnenden Arzt. Max. 3-5 Sätze.>"
}}
"""

_THERAPIEBERICHT_LANG_PROMPT = _BASE_PROMPT + """
## Berichtstyp: Therapiebericht lang (Bericht auf besondere Anforderung, Anhang C)

Dies ist ein ausführlicher Therapiebericht gemäß §16 Abs. 7 HeilM-RL.
Erstelle den Bericht mit exakt dieser JSON-Struktur:
{{
  "therapeutische_diagnostik": "<Beschreibung der durchgeführten diagnostischen Verfahren und deren Ergebnisse. Welche Tests/Screenings wurden eingesetzt? Welche Befunde ergaben sich?>",
  "aktueller_krankheitsstatus": "<Aktueller Status der Sprach-/Sprech-/Stimm-/Schluckstörung. Schweregrad, betroffene Bereiche, Auswirkung auf Kommunikation und Teilhabe.>",
  "aktueller_therapiestand": "<Beschreibung des bisherigen Therapieverlaufs: eingesetzte Methoden, erreichte Therapieziele, Fortschritte, Mitarbeit des Patienten/der Eltern, häusliches Üben.>",
  "weiteres_vorgehen": "<Geplantes weiteres therapeutisches Vorgehen: neue Therapieziele, geplante Methoden, empfohlene Frequenz, Prognose.>"
}}
"""

_ABSCHLUSSBERICHT_PROMPT = _BASE_PROMPT + """
## Berichtstyp: Abschlussbericht (Ende einer Verordnungsreihe)

Erstelle einen Abschlussbericht mit exakt dieser JSON-Struktur:
{{
  "therapieverlauf_zusammenfassung": "<Zusammenfassung des gesamten Therapieverlaufs: Therapiedauer, Anzahl Sitzungen, eingesetzte Methoden und Schwerpunkte, Kooperation.>",
  "ergebnis": "<Vergleich von Anfangs- und Endbefund. Welche Ziele wurden erreicht? Welche Verbesserungen sind eingetreten? Was konnte nicht erreicht werden?>",
  "empfehlung": "<Empfehlung: Entlassung aus der Therapie ODER Weiterführung mit neuer Verordnung. Begründung der Empfehlung. Ggf. Hinweise für den Alltag/Eigenübungen.>"
}}
"""

_PROMPT_MAP = {
    "befundbericht": _BEFUNDBERICHT_PROMPT,
    "therapiebericht_kurz": _THERAPIEBERICHT_KURZ_PROMPT,
    "therapiebericht_lang": _THERAPIEBERICHT_LANG_PROMPT,
    "abschlussbericht": _ABSCHLUSSBERICHT_PROMPT,
}


def _format_anamnesis_data(data: dict) -> str:
    """Format collected anamnesis data into a readable string for the prompt."""
    lines: list[str] = []
    field_labels = {
        "report_type": "Berichtstyp",
        "patient_pseudonym": "Patient (Pseudonym)",
        "age_group": "Altersgruppe",
        "gender": "Geschlecht",
        "indikationsschluessel": "Indikationsschlüssel",
        "icd_10_codes": "ICD-10 Codes",
        "diagnose_text": "Diagnose",
        "anamnese_persoenlich": "Persönliche Anamnese",
        "anamnese_familie": "Familienanamnese",
        "sprachentwicklung": "Sprachentwicklung",
        "motorische_entwicklung": "Motorische Entwicklung",
        "hoervermögen": "Hörvermögen",
        "mehrsprachigkeit": "Mehrsprachigkeit",
        "symptombeginn": "Symptombeginn",
        "ursache": "Ursache",
        "auswirkung_alltag": "Auswirkung auf Alltag",
        "bisherige_behandlung": "Bisherige Behandlung",
        "stimmbelastung": "Stimmbelastung",
        "hno_befund": "HNO-Befund",
        "kostform": "Kostform",
        "aspirationszeichen": "Aspirationszeichen",
        "therapieinhalte": "Therapieinhalte",
        "anzahl_sitzungen": "Anzahl Sitzungen",
        "fortschritte": "Fortschritte",
        "therapieziele": "Therapieziele",
        "kooperation": "Kooperation",
        "haeusliches_ueben": "Häusliches Üben",
        "zusaetzliche_infos": "Zusätzliche Informationen",
    }
    for key, label in field_labels.items():
        value = data.get(key)
        if value and value != [] and value != "":
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            lines.append(f"- **{label}:** {value}")
    return "\n".join(lines) if lines else "Keine Daten gesammelt."


def _format_materials(session: Session) -> str:
    """Format uploaded materials into a string for the prompt."""
    if not session.materials:
        return "Keine Materialien hochgeladen."
    parts: list[str] = []
    for mat in session.materials:
        text_preview = mat.extracted_text[:2000] if len(mat.extracted_text) > 2000 else mat.extracted_text
        parts.append(f"### {mat.filename} ({mat.material_type})\n{text_preview}")
    return "\n\n".join(parts)


def _build_patient_info(data: dict) -> PatientInfo:
    return PatientInfo(
        pseudonym=data.get("patient_pseudonym", "Patient"),
        age_group=data.get("age_group", "erwachsen"),
        gender=data.get("gender"),
    )


def _build_diagnose(data: dict) -> Diagnose:
    codes = data.get("icd_10_codes", [])
    if isinstance(codes, str):
        codes = [codes]
    return Diagnose(
        icd_10_codes=codes,
        indikationsschluessel=data.get("indikationsschluessel", ""),
        diagnose_text=data.get("diagnose_text", ""),
    )


class ReportGenerator:
    def __init__(self, groq: GroqService) -> None:
        self._groq = groq

    async def generate(self, session: Session) -> ReportUnion:
        """Generate a structured report from the session's collected data."""
        report_type = session.report_type or "befundbericht"
        prompt_template = _PROMPT_MAP.get(report_type, _BEFUNDBERICHT_PROMPT)

        anamnesis_text = _format_anamnesis_data(session.collected_data)
        materials_text = _format_materials(session)

        system_prompt = prompt_template.format(
            anamnesis_data=anamnesis_text,
            materials=materials_text,
        )

        messages = [
            {
                "role": "user",
                "content": "Bitte erstelle jetzt den Bericht auf Basis aller gesammelten Daten. "
                "Antworte ausschließlich mit dem JSON-Objekt.",
            }
        ]

        result = await self._groq.json_completion(messages, system_prompt)

        patient = _build_patient_info(session.collected_data)
        diagnose = _build_diagnose(session.collected_data)

        # Update diagnose_text from LLM if it provided one
        if result.get("diagnose_text"):
            diagnose.diagnose_text = result["diagnose_text"]

        if report_type == "befundbericht":
            return Befundbericht(
                patient=patient,
                anamnese=result.get("anamnese", ""),
                befund=result.get("befund", ""),
                diagnose=diagnose,
                therapieindikation=result.get("therapieindikation", ""),
                therapieziele=result.get("therapieziele", []),
                empfehlung=result.get("empfehlung", ""),
            )
        elif report_type == "therapiebericht_kurz":
            return TherapieberichtKurz(
                patient=patient,
                diagnose=diagnose,
                empfehlungen=result.get("empfehlungen", ""),
            )
        elif report_type == "therapiebericht_lang":
            return TherapieberichtLang(
                patient=patient,
                diagnose=diagnose,
                therapeutische_diagnostik=result.get("therapeutische_diagnostik", ""),
                aktueller_krankheitsstatus=result.get("aktueller_krankheitsstatus", ""),
                aktueller_therapiestand=result.get("aktueller_therapiestand", ""),
                weiteres_vorgehen=result.get("weiteres_vorgehen", ""),
            )
        else:  # abschlussbericht
            return Abschlussbericht(
                patient=patient,
                diagnose=diagnose,
                therapieverlauf_zusammenfassung=result.get("therapieverlauf_zusammenfassung", ""),
                ergebnis=result.get("ergebnis", ""),
                empfehlung=result.get("empfehlung", ""),
            )
