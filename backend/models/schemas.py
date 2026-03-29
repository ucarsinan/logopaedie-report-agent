from __future__ import annotations

from pydantic import BaseModel, Field


# ── Legacy model (kept for backward compatibility with /process-audio) ──────
class MedicalReport(BaseModel):
    patient_pseudonym: str
    symptoms: list[str]
    therapy_progress: str
    prognosis: str


# ── Session ─────────────────────────────────────────────────────────────────
class SessionInfo(BaseModel):
    session_id: str
    status: str = "anamnesis"  # anamnesis | materials | generating | complete
    report_type: str | None = None
    collected_data: dict = Field(default_factory=dict)


# ── Chat ────────────────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str | None = None


class ChatResponse(BaseModel):
    message: str
    phase: str  # greeting | report_type | patient_info | disorder | anamnesis | goals | summary
    is_anamnesis_complete: bool = False
    collected_fields: list[str] = Field(default_factory=list)


# ── Patient & Diagnose ──────────────────────────────────────────────────────
class PatientInfo(BaseModel):
    pseudonym: str = "Nicht angegeben"
    age_group: str = "erwachsen"  # kind | jugendlich | erwachsen
    gender: str | None = None


class Diagnose(BaseModel):
    icd_10_codes: list[str] = Field(default_factory=list)
    indikationsschluessel: str = ""  # SP1-SP6, ST1-ST2, SC1-SC2, RE1-RE2, SF
    diagnose_text: str = ""


# ── Report types ────────────────────────────────────────────────────────────
class Befundbericht(BaseModel):
    report_type: str = "befundbericht"
    patient: PatientInfo = Field(default_factory=PatientInfo)
    anamnese: str = ""
    befund: str = ""
    diagnose: Diagnose = Field(default_factory=Diagnose)
    therapieindikation: str = ""
    therapieziele: list[str] = Field(default_factory=list)
    empfehlung: str = ""


class TherapieberichtKurz(BaseModel):
    report_type: str = "therapiebericht_kurz"
    patient: PatientInfo = Field(default_factory=PatientInfo)
    diagnose: Diagnose = Field(default_factory=Diagnose)
    empfehlungen: str = ""


class TherapieberichtLang(BaseModel):
    report_type: str = "therapiebericht_lang"
    patient: PatientInfo = Field(default_factory=PatientInfo)
    diagnose: Diagnose = Field(default_factory=Diagnose)
    therapeutische_diagnostik: str = ""
    aktueller_krankheitsstatus: str = ""
    aktueller_therapiestand: str = ""
    weiteres_vorgehen: str = ""


class Abschlussbericht(BaseModel):
    report_type: str = "abschlussbericht"
    patient: PatientInfo = Field(default_factory=PatientInfo)
    diagnose: Diagnose = Field(default_factory=Diagnose)
    therapieverlauf_zusammenfassung: str = ""
    ergebnis: str = ""
    empfehlung: str = ""


# Union type for all reports
ReportUnion = Befundbericht | TherapieberichtKurz | TherapieberichtLang | Abschlussbericht

REPORT_TYPE_MAP: dict[str, type[ReportUnion]] = {
    "befundbericht": Befundbericht,
    "therapiebericht_kurz": TherapieberichtKurz,
    "therapiebericht_lang": TherapieberichtLang,
    "abschlussbericht": Abschlussbericht,
}


# ── File upload ─────────────────────────────────────────────────────────────
class UploadedMaterial(BaseModel):
    filename: str
    content_type: str
    extracted_text: str
    material_type: str = "sonstiges"  # alter_bericht | diagnostik | verordnung | sonstiges
