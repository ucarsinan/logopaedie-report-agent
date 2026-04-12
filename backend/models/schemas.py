from __future__ import annotations

from typing import Literal

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
    chat_history: list["ChatMessage"] = Field(default_factory=list)
    materials_consent: bool = False
    therapy_plan_mode: bool = False


# ── Chat ────────────────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    message: str | None = Field(default=None, max_length=5000)
    mode: Literal["guided", "quick_input"] = "guided"


class ChatResponse(BaseModel):
    message: str
    phase: str  # greeting | report_type | patient_info | disorder | anamnesis | goals | summary
    is_anamnesis_complete: bool = False
    collected_fields: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    transcript: str | None = None


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


# ── Therapy Plan persistence ────────────────────────────────────────────────
class TherapyPlanSummary(BaseModel):
    id: int
    created_at: str
    patient_pseudonym: str
    report_id: int | None = None


class TherapyPlanSaveRequest(BaseModel):
    session_id: str
    report_id: int | None = None
    plan_data: dict | None = None  # if provided, skip re-generation


# ── File upload ─────────────────────────────────────────────────────────────
class UploadedMaterial(BaseModel):
    filename: str
    content_type: str
    extracted_text: str
    material_type: str = "sonstiges"  # alter_bericht | diagnostik | verordnung | sonstiges


# ── Feature 1: Phonological Process Analysis ───────────────────────────────
class PhonologicalProcess(BaseModel):
    target_word: str
    production: str
    processes: list[str] = Field(default_factory=list)
    severity: str = "leicht"  # leicht | mittel | schwer


class PhonologicalAnalysis(BaseModel):
    items: list[PhonologicalProcess] = Field(default_factory=list)
    summary: str = ""
    age_appropriate: bool = True
    recommended_focus: list[str] = Field(default_factory=list)


# ── Feature 2: Therapy Plan Generator ──────────────────────────────────────
class TherapyGoal(BaseModel):
    icf_code: str = ""
    goal_text: str = ""
    methods: list[str] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)
    timeframe: str = ""


class TherapyPhase(BaseModel):
    phase_name: str = ""
    goals: list[TherapyGoal] = Field(default_factory=list)
    duration: str = ""


class TherapyPlan(BaseModel):
    patient_pseudonym: str = ""
    diagnose_text: str = ""
    plan_phases: list[TherapyPhase] = Field(default_factory=list)
    frequency: str = ""
    total_sessions: int = 0
    elternberatung: str = ""
    haeusliche_uebungen: list[str] = Field(default_factory=list)


# ── Feature 3: Comparative Report Analysis ─────────────────────────────────
class ComparisonItem(BaseModel):
    category: str = ""
    initial_finding: str = ""
    current_finding: str = ""
    change: str = "unverändert"  # verbessert | unverändert | verschlechtert
    details: str = ""


class ReportComparison(BaseModel):
    items: list[ComparisonItem] = Field(default_factory=list)
    overall_progress: str = ""
    remaining_issues: list[str] = Field(default_factory=list)
    recommendation: str = ""


# ── Feature 4: Intelligent Text Suggestions ────────────────────────────────
class SuggestRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    report_type: str = Field(default="befundbericht", max_length=100)
    disorder: str = Field(default="", max_length=200)
    section: str = Field(default="", max_length=100)  # z.B. "anamnese", "befund", "therapieindikation"


class TextSuggestion(BaseModel):
    suggestions: list[str] = Field(default_factory=list)
