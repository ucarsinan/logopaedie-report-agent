import type {
  ChatResponse,
  ReportData,
  ReportDetail,
  ReportListResponse,
  ReportStats,
  ReportFilterParams,
  SOAPNote,
  TherapyPlanSummary,
  UploadedFile,
} from "@/types";
import type { TherapyPlanData } from "@/types/therapy-plan";
import type { PhonologicalAnalysisData, ReportComparisonData } from "@/types/phonology";

export { REPORT_TYPE_LABELS } from "@/types";
export type { ReportSummary, ReportDetail, TherapyPlanSummary } from "@/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

/* ═══════════════════════════════ Shared fetch helper ═════════════════════════ */

async function fetchApi<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(`${API}${path}`, init);
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? res.statusText);
  }
  return res.json();
}

/* ═══════════════════════════════ API Object ══════════════════════════════════ */

export const api = {
  health: () => fetchApi<{ status: string }>("/health"),

  sessions: {
    create: (mode?: string) =>
      fetchApi<{ session_id: string; collected_data?: { greeting?: string } }>(
        "/sessions",
        {
          method: "POST",
          ...(mode
            ? {
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ mode }),
              }
            : {}),
        },
      ),

    get: (id: string) =>
      fetchApi<{
        session_id: string;
        status: string;
        chat_history?: { role: string; content: string }[];
        collected_data?: {
          greeting?: string;
          current_phase?: string;
          collected_fields?: string[];
          missing_fields?: string[];
        };
        materials_consent?: boolean;
      }>(`/sessions/${id}`),

    chat: (id: string, message: string, mode?: string) =>
      fetchApi<ChatResponse>(`/sessions/${id}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, ...(mode ? { mode } : {}) }),
      }),

    audio: (id: string, blob: Blob) => {
      const formData = new FormData();
      formData.append("audio_file", blob, "recording.webm");
      return fetchApi<ChatResponse>(`/sessions/${id}/audio`, {
        method: "POST",
        body: formData,
      });
    },

    upload: (id: string, file: File, materialType = "sonstiges") => {
      const formData = new FormData();
      formData.append("file", file);
      return fetchApi<UploadedFile>(
        `/sessions/${id}/upload?material_type=${encodeURIComponent(materialType)}`,
        { method: "POST", body: formData },
      );
    },

    consent: (id: string, consent: boolean) =>
      fetchApi<void>(`/sessions/${id}/materials-consent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ consent }),
      }),

    generate: (id: string) =>
      fetchApi<ReportData & { _db_id?: number }>(`/sessions/${id}/generate`, {
        method: "POST",
      }),

    report: (id: string) => fetchApi<ReportData>(`/sessions/${id}/report`),

    newConversation: (id: string) =>
      fetchApi<{ collected_data?: { greeting?: string } }>(
        `/sessions/${id}/new-conversation`,
        { method: "POST" },
      ),

    therapyPlan: (id: string) =>
      fetchApi<TherapyPlanData>(`/sessions/${id}/therapy-plan`, {
        method: "POST",
      }),
  },

  reports: {
    list: (params?: ReportFilterParams): Promise<ReportListResponse> => {
      const qs = new URLSearchParams();
      if (params?.pseudonym) qs.set("pseudonym", params.pseudonym);
      if (params?.report_type) qs.set("report_type", params.report_type);
      if (params?.from_date) qs.set("from_date", params.from_date);
      if (params?.to_date) qs.set("to_date", params.to_date);
      if (params?.page) qs.set("page", String(params.page));
      if (params?.limit) qs.set("limit", String(params.limit));
      const q = qs.toString();
      return fetchApi<ReportListResponse>(`/reports${q ? `?${q}` : ""}`);
    },
    get: (id: number): Promise<ReportDetail> =>
      fetchApi<ReportDetail>(`/reports/${id}`),
    stats: (): Promise<ReportStats> =>
      fetchApi<ReportStats>("/reports/stats"),
    downloadPdf: async (id: number): Promise<Blob> => {
      const res = await fetch(`${API}/reports/${id}/pdf`);
      if (!res.ok) throw new Error("PDF-Download fehlgeschlagen");
      return res.blob();
    },
  },

  soap: {
    generate: (sessionId: string): Promise<SOAPNote> =>
      fetchApi<SOAPNote>(`/sessions/${sessionId}/soap`, { method: "POST" }),
    get: (id: number): Promise<SOAPNote> =>
      fetchApi<SOAPNote>(`/soap/${id}`),
    fromReport: (reportId: number): Promise<SOAPNote> =>
      fetchApi<SOAPNote>(`/reports/${reportId}/soap`, { method: "POST" }),
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
    save: async (
      sessionId: string,
      planData: Record<string, unknown>,
      reportId?: number,
    ): Promise<TherapyPlanSummary> => {
      const res = await fetch(`${API}/therapy-plans`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          plan_data: planData,
          report_id: reportId ?? null,
        }),
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
      if (!res.ok)
        throw new Error("Fehler beim Aktualisieren des Therapieplans");
    },
  },

  analysis: {
    phonologicalText: (
      pairs: { target: string; production: string }[],
      ageGroup?: string,
    ) =>
      fetchApi<PhonologicalAnalysisData>(
        `/analysis/phonological-text${ageGroup ? `?child_age=${encodeURIComponent(ageGroup)}` : ""}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(pairs),
        },
      ),

    compare: (initialReport: File, currentReport: File) => {
      const formData = new FormData();
      formData.append("initial_report", initialReport);
      formData.append("current_report", currentReport);
      return fetchApi<ReportComparisonData>("/analysis/compare", {
        method: "POST",
        body: formData,
      });
    },
  },

  suggest: (
    text: string,
    reportType?: string,
    disorder?: string,
    section?: string,
  ) =>
    fetchApi<{ suggestions: string[] }>("/suggest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, report_type: reportType, disorder, section }),
    }),

  transcribe: (blob: Blob) => {
    const form = new FormData();
    form.append("audio_file", blob, "recording.webm");
    return fetchApi<{ transcript?: string }>("/transcribe", {
      method: "POST",
      body: form,
    });
  },
};
