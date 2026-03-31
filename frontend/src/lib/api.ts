const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface TherapyPlanSummary {
  id: number;
  created_at: string;
  patient_pseudonym: string;
  report_id: number | null;
}

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

export const REPORT_TYPE_LABELS: Record<string, string> = {
  befundbericht: "Befundbericht",
  therapiebericht_kurz: "Therapiebericht (kurz)",
  therapiebericht_lang: "Therapiebericht (lang)",
  abschlussbericht: "Abschlussbericht",
};

export const api = {
  reports: {
    list: async (): Promise<ReportSummary[]> => {
      const res = await fetch(`${API}/reports`);
      if (!res.ok) throw new Error("Fehler beim Laden der Berichte");
      return res.json();
    },
    get: async (id: number): Promise<ReportDetail> => {
      const res = await fetch(`${API}/reports/${id}`);
      if (!res.ok) throw new Error("Bericht nicht gefunden");
      return res.json();
    },
  },
  therapyPlans: {
    list: async (): Promise<TherapyPlanSummary[]> => {
      const res = await fetch(`${API}/therapy-plans`);
      if (!res.ok) throw new Error("Fehler beim Laden der Therapiepläne");
      return res.json();
    },
    get: async (id: number): Promise<Record<string, unknown>> => {
      const res = await fetch(`${API}/therapy-plans/${id}`);
      if (!res.ok) throw new Error("Therapieplan nicht gefunden");
      return res.json();
    },
    save: async (sessionId: string, planData: Record<string, unknown>, reportId?: number): Promise<TherapyPlanSummary> => {
      const res = await fetch(`${API}/therapy-plans`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, plan_data: planData, report_id: reportId ?? null }),
      });
      if (!res.ok) throw new Error("Fehler beim Speichern des Therapieplans");
      return res.json();
    },
    update: async (id: number, plan: Record<string, unknown>): Promise<void> => {
      const res = await fetch(`${API}/therapy-plans/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(plan),
      });
      if (!res.ok) throw new Error("Fehler beim Aktualisieren des Therapieplans");
    },
  },
};
