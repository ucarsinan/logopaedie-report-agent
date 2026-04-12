/* ═══════════════════════════════ Shared Types ═════════════════════════════════ */

export interface ChatMsg {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  message: string;
  phase: string;
  is_anamnesis_complete: boolean;
  collected_fields: string[];
  missing_fields: string[];
  transcript?: string;
}

export interface UploadedFile {
  filename: string;
  material_type: string;
  extracted_text: string;
}

export interface DiagnoseData {
  icd_10_codes: string[];
  indikationsschluessel: string;
  diagnose_text: string;
}

export interface PatientData {
  pseudonym: string;
  age_group: string;
  gender: string | null;
}

// Union report shape -- fields vary by report_type
export interface ReportData {
  report_type: string;
  patient: PatientData;
  diagnose: DiagnoseData;
  // befundbericht
  anamnese?: string;
  befund?: string;
  therapieindikation?: string;
  therapieziele?: string[];
  empfehlung?: string;
  // therapiebericht_kurz
  empfehlungen?: string;
  // therapiebericht_lang
  therapeutische_diagnostik?: string;
  aktueller_krankheitsstatus?: string;
  aktueller_therapiestand?: string;
  weiteres_vorgehen?: string;
  // abschlussbericht
  therapieverlauf_zusammenfassung?: string;
  ergebnis?: string;
}

export type AppPhase = "pre-upload" | "chat" | "generating" | "preview";
export type AppModule = "report" | "phonology" | "therapy-plan" | "compare" | "suggest" | "history" | "soap";

/* ═══════════════════════════════ Report List/Stats ═══════════════════════════ */

export interface ReportListResponse {
  items: ReportSummary[];
  total: number;
  page: number;
  limit: number;
}

export interface ReportStats {
  total: number;
  by_type: Record<string, number>;
  latest_date: string | null;
}

export interface ReportFilterParams {
  pseudonym?: string;
  report_type?: string;
  from_date?: string;
  to_date?: string;
  page?: number;
  limit?: number;
}

/* ═══════════════════════════════ SOAP Notes ══════════════════════════════════ */

export interface SOAPNote {
  id?: number;
  report_id?: number | null;
  session_id?: string | null;
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
  created_at?: string;
}

/* ═══════════════════════════════ Report Types ═════════════════════════════════ */

export interface ReportSummary {
  id: number;
  pseudonym: string;
  report_type: string;
  created_at: string;
}

export interface ReportDetail extends ReportSummary {
  patient?: { pseudonym: string; age_group: string; gender: string | null };
  diagnose?: { icd_10_codes: string[]; indikationsschluessel: string; diagnose_text: string };
  anamnese?: string;
  befund?: string;
  therapieindikation?: string;
  therapieziele?: string[];
  empfehlung?: string;
  empfehlungen?: string;
  therapeutische_diagnostik?: string;
  aktueller_krankheitsstatus?: string;
  aktueller_therapiestand?: string;
  weiteres_vorgehen?: string;
  therapieverlauf_zusammenfassung?: string;
  ergebnis?: string;
  _db_id?: number;
  [key: string]: unknown;
}

/* ═══════════════════════════════ Constants ════════════════════════════════════ */

/** Single source of truth for report type display labels */
export const REPORT_TYPE_LABELS: Record<string, string> = {
  befundbericht: "Befundbericht",
  therapiebericht_kurz: "Therapiebericht (kurz)",
  therapiebericht_lang: "Therapiebericht (lang)",
  abschlussbericht: "Abschlussbericht",
};

/* ═══════════════════════════════ Therapy Plan Summary ═════════════════════════ */

export interface TherapyPlanSummary {
  id: number;
  created_at: string;
  patient_pseudonym: string;
  report_id: number | null;
}
