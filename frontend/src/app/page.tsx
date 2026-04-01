"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ResetConfirmDialog } from "@/components/ResetConfirmDialog";
import { WorkflowStepper } from "@/components/WorkflowStepper";
import { OnboardingOverlay } from "@/components/OnboardingOverlay";
import type { StepConfig } from "@/components/WorkflowStepper";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Link from "next/link";
import { ReportSummary, ReportDetail, REPORT_TYPE_LABELS, api as reportsApi } from "@/lib/api";

/* ═══════════════════════════════════ Types ═══════════════════════════════════ */

interface ChatMsg {
  role: "user" | "assistant";
  content: string;
}

interface ChatResponse {
  message: string;
  phase: string;
  is_anamnesis_complete: boolean;
  collected_fields: string[];
  missing_fields: string[];
  transcript?: string;
}

interface UploadedFile {
  filename: string;
  material_type: string;
  extracted_text: string;
}

interface DiagnoseData {
  icd_10_codes: string[];
  indikationsschluessel: string;
  diagnose_text: string;
}

interface PatientData {
  pseudonym: string;
  age_group: string;
  gender: string | null;
}

// Union report shape – fields vary by report_type
interface ReportData {
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

type AppPhase = "pre-upload" | "chat" | "generating" | "preview";
type AppModule = "report" | "phonology" | "therapy-plan" | "compare" | "suggest" | "history";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SESSION_STORAGE_KEY = "logopaedie_session_id";

const REPORT_STEPS: StepConfig[] = [
  {
    label: "Unterlagen",
    infoTitle: "Vorhandene Unterlagen hochladen",
    infoText:
      "Laden Sie frühere Berichte, Diagnostik oder Verordnungen hoch. Die KI berücksichtigt diese und stellt gezieltere Fragen — das spart Zeit im Gespräch.",
  },
  {
    label: "Gespräch",
    infoTitle: "Anamnesegespräch",
    infoText:
      "Beantworten Sie die Fragen des Assistenten. Je vollständiger Ihre Angaben, desto präziser der generierte Bericht.",
  },
  {
    label: "Generierung",
    infoTitle: "Bericht wird generiert",
    infoText:
      "Der KI-Assistent erstellt jetzt Ihren Bericht auf Basis des Gesprächs. Dies dauert wenige Sekunden.",
  },
  {
    label: "Vorschau",
    infoTitle: "Bericht fertig",
    infoText:
      "Prüfen Sie den generierten Bericht. Klicken Sie auf abgeschlossene Schritte (✓) um zurückzunavigieren — Ihre Daten bleiben erhalten.",
    infoVariant: "success",
  },
];

const PHASE_TO_STEP: Record<string, number> = {
  "pre-upload": 0,
  chat: 1,
  generating: 2,
  preview: 3,
};

const STEP_TO_PHASE: Record<number, AppPhase> = {
  0: "pre-upload",
  1: "chat",
  2: "generating",
  3: "preview",
};

/* ═══════════════════════════ Feature Types ═══════════════════════════════ */

interface PhonologicalProcess {
  target_word: string;
  production: string;
  processes: string[];
  severity: string;
}

interface PhonologicalAnalysisData {
  items: PhonologicalProcess[];
  summary: string;
  age_appropriate: boolean;
  recommended_focus: string[];
}

interface TherapyGoal {
  icf_code: string;
  goal_text: string;
  methods: string[];
  milestones: string[];
  timeframe: string;
}

interface TherapyPhaseData {
  phase_name: string;
  goals: TherapyGoal[];
  duration: string;
}

interface TherapyPlanData {
  patient_pseudonym: string;
  diagnose_text: string;
  plan_phases: TherapyPhaseData[];
  frequency: string;
  total_sessions: number;
  elternberatung: string;
  haeusliche_uebungen: string[];
}

interface ComparisonItem {
  category: string;
  initial_finding: string;
  current_finding: string;
  change: string;
  details: string;
}

interface ReportComparisonData {
  items: ComparisonItem[];
  overall_progress: string;
  remaining_issues: string[];
  recommendation: string;
}

/* ═══════════════════════════════ Main Component ═════════════════════════════ */

export default function Home() {
  const [activeModule, setActiveModule] = useState<AppModule>("report");

  useEffect(() => {
    const m = new URLSearchParams(window.location.search).get("module");
    const valid: AppModule[] = ["report", "phonology", "therapy-plan", "compare", "suggest"];
    if (valid.includes(m as AppModule)) {
      setActiveModule(m as AppModule);
    }
  }, []);

  const handleModuleChange = (module: AppModule) => {
    setActiveModule(module);
    const url = new URL(window.location.href);
    url.searchParams.set("module", module);
    window.history.replaceState({}, "", url.toString());
  };
  const [phase, setPhase] = useState<AppPhase>("pre-upload");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isAnamnesisComplete, setIsAnamnesisComplete] = useState(false);
  const [collectedFields, setCollectedFields] = useState<string[]>([]);
  const [missingFields, setMissingFields] = useState<string[]>([]);
  const [currentPhase, setCurrentPhase] = useState("greeting");
  const [inputMode, setInputMode] = useState<"select" | "free" | "guided">("select");
  const [freeText, setFreeText] = useState("");
  const [freeTextReportType, setFreeTextReportType] = useState<string>("");
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [report, setReport] = useState<ReportData | null>(null);
  const [savedReportId, setSavedReportId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isResetDialogOpen, setIsResetDialogOpen] = useState(false);
  const [consentChecked, setConsentChecked] = useState(false);
  const [materialsConsent, setMaterialsConsent] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);

  // Audio recording
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const chatInputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ⌘K / Ctrl+K → focus chat input
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        chatInputRef.current?.focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  // ── Create or restore session on mount ────────────────────────────
  useEffect(() => {
    async function init() {
      try {
        const storedId = localStorage.getItem(SESSION_STORAGE_KEY);
        if (storedId) {
          const res = await fetch(`${API}/sessions/${storedId}`);
          if (res.ok) {
            const data = await res.json();
            setSessionId(data.session_id);
            if (data.chat_history?.length > 0) {
              setMessages(
                data.chat_history.map((m: { role: string; content: string }) => ({
                  role: m.role as "user" | "assistant",
                  content: m.content,
                }))
              );
            }
            setIsAnamnesisComplete(data.status !== "anamnesis");
            if (data.collected_data?.current_phase) {
              setCurrentPhase(data.collected_data.current_phase);
            }
            if (data.collected_data?.collected_fields) {
              setCollectedFields(data.collected_data.collected_fields);
            }
            if (data.materials_consent) {
              setMaterialsConsent(true);
              setConsentChecked(true);
            }
            setPhase("chat");
            return;
          }
          // Session abgelaufen oder nicht gefunden
          localStorage.removeItem(SESSION_STORAGE_KEY);
        }

        // Neue Session erstellen
        const res = await fetch(`${API}/sessions`, { method: "POST" });
        if (!res.ok) throw new Error("Session konnte nicht erstellt werden.");
        const data = await res.json();
        setSessionId(data.session_id);
        localStorage.setItem(SESSION_STORAGE_KEY, data.session_id);
        if (data.collected_data?.greeting) {
          setMessages([{ role: "assistant", content: data.collected_data.greeting }]);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Verbindung fehlgeschlagen.");
      }
    }
    init();
    // Onboarding nur beim ersten Besuch
    if (typeof window !== "undefined" && !localStorage.getItem("logopaedie_onboarding_done")) {
      setShowOnboarding(true);
    }
  }, []);

  // ── Send text message ──────────────────────────────────────────────
  const sendMessage = useCallback(
    async (text: string) => {
      if (!sessionId || !text.trim()) return;
      setError(null);
      setIsSending(true);
      setMessages((prev) => [...prev, { role: "user", content: text }]);
      setInput("");

      try {
        const res = await fetch(`${API}/sessions/${sessionId}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text }),
        });
        if (!res.ok) {
          const detail = await res.json().catch(() => null);
          throw new Error(detail?.detail ?? "Fehler beim Senden.");
        }
        const data: ChatResponse = await res.json();
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.message },
        ]);
        setCurrentPhase(data.phase);
        setIsAnamnesisComplete(data.is_anamnesis_complete);
        setCollectedFields(data.collected_fields);
        setMissingFields(data.missing_fields ?? []);
      } catch (err) {
        setMessages((prev) => prev.slice(0, -1)); // rollback user message
        setError(err instanceof Error ? err.message : "Unbekannter Fehler.");
      } finally {
        setIsSending(false);
      }
    },
    [sessionId]
  );

  // ── Send free-text (quick_input mode) ─────────────────────────────
  const sendFreeText = useCallback(async () => {
    if (!freeText.trim() || !freeTextReportType || isSending || !sessionId) return;

    const combinedMessage = `Berichtstyp: ${freeTextReportType}\n\n${freeText}`;

    setIsSending(true);
    setMessages((prev) => [...prev, { role: "user" as const, content: freeText }]);
    setFreeText("");

    try {
      const res = await fetch(`${API}/sessions/${sessionId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: combinedMessage, mode: "quick_input" }),
      });

      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail ?? `HTTP ${res.status}`);
      }

      const data: ChatResponse = await res.json();
      setMessages((prev) => [...prev, { role: "assistant" as const, content: data.message }]);
      setCurrentPhase(data.phase);
      setIsAnamnesisComplete(data.is_anamnesis_complete);
      setCollectedFields(data.collected_fields ?? []);
      setMissingFields(data.missing_fields ?? []);
    } catch (err) {
      setMessages((prev) => prev.slice(0, -1));
      setError(err instanceof Error ? err.message : "Fehler beim Senden. Bitte erneut versuchen.");
    } finally {
      setIsSending(false);
    }
  }, [sessionId, freeText, freeTextReportType, isSending]);

  // ── Audio recording ────────────────────────────────────────────────
  async function startRecording() {
    setError(null);
    audioChunksRef.current = [];
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        setIsTranscribing(true);
        try {
          const form = new FormData();
          form.append("audio_file", blob, "recording.webm");
          const res = await fetch(`${API}/transcribe`, { method: "POST", body: form });
          if (res.ok) {
            const data = await res.json();
            if (data.transcript) {
              setInput((prev) => prev ? prev + " " + data.transcript : data.transcript);
              chatInputRef.current?.focus();
            }
          }
        } catch {
          setError("Transkription fehlgeschlagen.");
        } finally {
          setIsTranscribing(false);
        }
      };
      recorder.start();
      setIsRecording(true);
    } catch {
      setError("Mikrofon-Zugriff verweigert oder nicht verfügbar.");
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  }

  async function sendAudio(blob: Blob) {
    if (!sessionId) return;
    setIsSending(true);
    setError(null);
    setMessages((prev) => [
      ...prev,
      { role: "user", content: "🎤 Sprachnachricht wird verarbeitet…" },
    ]);

    const formData = new FormData();
    formData.append("audio_file", blob, "recording.webm");

    try {
      const res = await fetch(`${API}/sessions/${sessionId}/audio`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail ?? "Audio-Verarbeitung fehlgeschlagen.");
      }
      const data: ChatResponse = await res.json();
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: "user", content: data.transcript ?? "🎤 (Sprachnachricht)" },
        { role: "assistant", content: data.message },
      ]);
      setCurrentPhase(data.phase);
      setIsAnamnesisComplete(data.is_anamnesis_complete);
      setCollectedFields(data.collected_fields);
      setMissingFields(data.missing_fields ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unbekannter Fehler.");
    } finally {
      setIsSending(false);
    }
  }

  // ── File upload ────────────────────────────────────────────────────
  async function handleFileUpload(files: FileList) {
    if (!sessionId) return;
    setError(null);

    for (const file of Array.from(files)) {
      const formData = new FormData();
      formData.append("file", file);

      try {
        const res = await fetch(
          `${API}/sessions/${sessionId}/upload?material_type=sonstiges`,
          { method: "POST", body: formData }
        );
        if (!res.ok) {
          const detail = await res.json().catch(() => null);
          throw new Error(detail?.detail ?? `Upload von ${file.name} fehlgeschlagen.`);
        }
        const data = await res.json();
        setUploadedFiles((prev) => [...prev, data]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload fehlgeschlagen.");
      }
    }
  }

  // ── Consent and proceed to chat ────────────────────────────────────
  async function handleConsentAndProceed() {
    if (!sessionId) return;
    try {
      await fetch(`${API}/sessions/${sessionId}/materials-consent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ consent: true }),
      });
      setMaterialsConsent(true);
    } catch {
      // Proceed even if consent request fails — fallback to no-material mode
    }
    setPhase("chat");
  }

  // ── Generate report ────────────────────────────────────────────────
  async function generateReport() {
    if (!sessionId) return;
    setPhase("generating");
    setError(null);

    try {
      const res = await fetch(`${API}/sessions/${sessionId}/generate`, {
        method: "POST",
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail ?? "Berichtgenerierung fehlgeschlagen.");
      }
      const data = await res.json();
      setReport(data);
      if ((data as { _db_id?: number })._db_id) {
        setSavedReportId((data as { _db_id: number })._db_id);
      }
      setPhase("preview");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unbekannter Fehler.");
      setPhase("chat");
    }
  }

  // ── Reset handlers ─────────────────────────────────────────────────────────────────────────────────────────────────
  const handleSoftReset = useCallback(async () => {
    if (!sessionId) return;
    setIsSending(true);
    setError(null);
    try {
      const res = await fetch(`${API}/sessions/${sessionId}/new-conversation`, {
        method: "POST",
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail ?? "Zurücksetzen fehlgeschlagen.");
      }
      const data = await res.json();
      setMessages(
        data.collected_data?.greeting
          ? [{ role: "assistant", content: data.collected_data.greeting }]
          : []
      );
      setPhase("pre-upload");
      setIsAnamnesisComplete(false);
      setCollectedFields([]);
      setMissingFields([]);
      setCurrentPhase("greeting");
      setInputMode("select");
      setFreeText("");
      setFreeTextReportType("");
      setUploadedFiles([]);
      setConsentChecked(false);
      setMaterialsConsent(false);
      setReport(null);
      setSavedReportId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unbekannter Fehler.");
    } finally {
      setIsSending(false);
      setIsResetDialogOpen(false);
    }
  }, [sessionId]);

  const handleFullReset = useCallback(async () => {
    setIsSending(true);
    setError(null);
    try {
      const res = await fetch(`${API}/sessions`, { method: "POST" });
      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail ?? "Neue Session konnte nicht erstellt werden.");
      }
      const data = await res.json();
      setSessionId(data.session_id);
      localStorage.setItem(SESSION_STORAGE_KEY, data.session_id);
      setMessages(
        data.collected_data?.greeting
          ? [{ role: "assistant", content: data.collected_data.greeting }]
          : []
      );
      setPhase("pre-upload");
      setIsAnamnesisComplete(false);
      setCollectedFields([]);
      setMissingFields([]);
      setCurrentPhase("greeting");
      setInputMode("select");
      setFreeText("");
      setFreeTextReportType("");
      setUploadedFiles([]);
      setConsentChecked(false);
      setMaterialsConsent(false);
      setReport(null);
      setSavedReportId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unbekannter Fehler.");
    } finally {
      setIsSending(false);
      setIsResetDialogOpen(false);
    }
  }, []);

  const handleOnboardingComplete = useCallback(() => {
    localStorage.setItem("logopaedie_onboarding_done", "true");
    setShowOnboarding(false);
  }, []);

  const handleOpenOnboarding = useCallback(() => {
    setShowOnboarding(true);
  }, []);

  // ── Render ─────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Header */}
      <header className="border-b border-border print:hidden">
        <div className="max-w-5xl mx-auto px-6">
          {/* Top bar: breadcrumb + controls */}
          <div className="flex items-center justify-between h-12">
            <div className="flex items-center gap-2 text-sm">
              <span className="font-extrabold tracking-tight text-foreground">
                Logopädie
              </span>
              <span className="text-border-strong font-light">/</span>
              <span className="font-semibold" style={{ color: "var(--accent-text)" }}>
                {({
                  report: "Berichterstellung",
                  phonology: "Ausspracheanalyse",
                  "therapy-plan": "Therapieplan",
                  compare: "Berichtsvergleich",
                  suggest: "Textbausteine",
                  history: "Bericht-Verlauf",
                } as Record<AppModule, string>)[activeModule]}
              </span>
            </div>
            <div className="flex items-center gap-3">
{messages.length > 0 && activeModule === "report" && (
                <button
                  onClick={() => setIsResetDialogOpen(true)}
                  className="text-sm text-muted-foreground hover:text-foreground px-2 py-1 rounded transition-colors"
                >
                  Neue Sitzung
                </button>
              )}
              <Link
                href="/berichte"
                className="text-xs text-muted-foreground hover:text-foreground border border-border rounded-full px-2.5 py-0.5 transition-colors"
                title="Gespeicherte Berichte anzeigen"
              >
                Verlauf
              </Link>
              <button
                onClick={handleOpenOnboarding}
                className="text-xs text-muted-foreground hover:text-foreground border border-border rounded-full px-2.5 py-0.5 transition-colors"
                title="Einführung anzeigen"
              >
                ? Hilfe
              </button>
              <ThemeToggle />
            </div>
          </div>

          {/* Module tabs */}
          <nav className="flex gap-1 -mb-px overflow-x-auto">
            {([
              ["report", "Berichterstellung", "KI-geführtes Anamnesegespräch → professioneller Bericht"],
              ["phonology", "Ausspracheanalyse", "Phonologische Prozesse aus Wortpaaren automatisch erkennen"],
              ["therapy-plan", "Therapieplan", "ICF-basierten Therapieplan automatisch generieren"],
              ["compare", "Berichtsvergleich", "Zwei Berichte gegenüberstellen und Fortschritt messen"],
              ["suggest", "Textbausteine", "KI-Formulierungsvorschläge während des Schreibens"],
              ["history", "Bericht-Verlauf", "Alle gespeicherten Berichte anzeigen und durchsuchen"],
            ] as [AppModule, string, string][]).map(([key, label, tooltip]) => (
              <button
                key={key}
                onClick={() => handleModuleChange(key)}
                title={tooltip}
                className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  activeModule === key
                    ? "border-[var(--accent)] text-[var(--accent-text)]"
                    : "border-transparent text-muted-foreground hover:text-foreground hover:border-border-strong"
                }`}
              >
                {label}
              </button>
            ))}
          </nav>

        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-8 flex flex-col gap-6">
        {/* Error — hidden on WelcomeScreen (shown inline there instead) */}
        {error && (
          <div
            role="alert"
            className="rounded-lg bg-error-surface border border-error-border px-5 py-4 text-sm text-error-text flex items-start gap-3 print:hidden"
          >
            <AlertIcon />
            <span>{error}</span>
          </div>
        )}

        {/* ── Module: Phonological Analysis ─────────────────────── */}
        {activeModule === "phonology" && (
          <PhonologicalAnalysisView api={API} />
        )}

        {/* ── Module: Therapy Plan ──────────────────────────────── */}
        {activeModule === "therapy-plan" && (
          <TherapyPlanView api={API} sessionId={sessionId} />
        )}

        {/* ── Module: Report Comparison ─────────────────────────── */}
        {activeModule === "compare" && (
          <ReportComparisonView api={API} />
        )}

        {/* ── Module: Text Suggestions ──────────────────────────── */}
        {activeModule === "suggest" && (
          <TextSuggestionView api={API} />
        )}

        {/* ── Module: Report History ────────────────────────────── */}
        {activeModule === "history" && (
          <HistoryView />
        )}

        {/* ── Berichterstellung: Workflow-Stepper ────────────────── */}
        {activeModule === "report" && (
          <WorkflowStepper
            steps={REPORT_STEPS}
            currentStep={PHASE_TO_STEP[phase] ?? 0}
            onStepClick={phase !== "generating" ? (i) => setPhase(STEP_TO_PHASE[i]) : undefined}
          />
        )}

        {/* ── Module: Report (original phases) ──────────────────── */}
        {activeModule === "report" && phase === "chat" && (
          <>
            {currentPhase !== "greeting" && (
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <h1 className="text-xl font-semibold tracking-tight">
                    Anamnese-Gespräch
                  </h1>
                  {missingFields.length > 0 ? (
                    <span className="text-xs text-muted-foreground">
                      {missingFields.length} Pflichtfelder offen
                    </span>
                  ) : collectedFields.length > 0 ? (
                    <span className="text-xs" style={{ color: "var(--accent-text)" }}>
                      Alle Pflichtfelder erfasst
                    </span>
                  ) : null}
                </div>
                <AnamnesisProgress currentPhase={currentPhase} />
              </div>
            )}

            {/* Chat messages */}
            <div className="flex-1 flex flex-col gap-3 overflow-y-auto max-h-[60vh] rounded-lg border border-border bg-surface p-4 card-elevated">
              {messages.map((msg, i) => (
                <ChatBubble key={i} role={msg.role} content={msg.content} />
              ))}
              {currentPhase === "greeting" && inputMode === "select" && (
                <ModeSelectionCards onSelect={(mode) => setInputMode(mode)} />
              )}
              {currentPhase === "greeting" && inputMode === "guided" && (
                <QuickReplyBubbles onSelect={sendMessage} disabled={isSending} />
              )}
              {currentPhase === "greeting" && inputMode === "free" && (
                <FreeTextInput
                  reportType={freeTextReportType}
                  onReportTypeChange={setFreeTextReportType}
                  value={freeText}
                  onChange={setFreeText}
                  onSubmit={sendFreeText}
                  disabled={isSending}
                  apiUrl={API}
                />
              )}
              {isSending && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Spinner /> Antwort wird generiert…
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Input area — hidden during greeting phase */}
            {currentPhase !== "greeting" && (
              <div className="flex gap-2 print:hidden">
                <input
                  ref={chatInputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      sendMessage(input);
                    }
                  }}
                  disabled={isSending}
                  placeholder="Ihre Antwort eingeben…"
                  className="flex-1 rounded-lg bg-input border border-border-strong px-4 py-3 text-sm text-foreground placeholder:text-muted focus:outline-none focus:border-ring disabled:opacity-40"
                />
                {isTranscribing ? (
                  <button disabled className="px-4 py-3 rounded-lg bg-surface-elevated text-foreground/40" title="Transkribiert…">
                    ⏳
                  </button>
                ) : !isRecording ? (
                  <button
                    onClick={startRecording}
                    disabled={isSending}
                    className="px-4 py-3 rounded-lg bg-surface-elevated hover:bg-border-strong text-foreground/80 transition-colors disabled:opacity-40"
                    title="Spracheingabe"
                  >
                    <MicIcon />
                  </button>
                ) : (
                  <button
                    onClick={stopRecording}
                    className="px-4 py-3 rounded-lg bg-red-600 text-white motion-safe:animate-pulse"
                    title="Aufnahme stoppen"
                  >
                    <StopIcon />
                  </button>
                )}
                <button
                  onClick={() => sendMessage(input)}
                  disabled={isSending || isTranscribing || !input.trim()}
                  className="px-6 py-3 rounded-lg bg-accent hover:bg-accent-hover text-white font-medium text-sm transition-colors disabled:opacity-40 btn-accent-glow"
                >
                  Senden
                </button>
              </div>
            )}

            {/* Transition to generating */}
            {isAnamnesisComplete && (
              <div className="flex items-center gap-3 rounded-lg border border-accent px-5 py-4 bg-accent-muted">
                <span className="text-sm text-accent-text">
                  Anamnese abgeschlossen! Sie können den Bericht jetzt generieren.
                </span>
                <button
                  onClick={generateReport}
                  className="shrink-0 px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors btn-accent-glow"
                >
                  Bericht generieren
                </button>
              </div>
            )}
          </>
        )}

        {/* ── Phase: Pre-Upload ──────────────────────────────────── */}
        {activeModule === "report" && phase === "pre-upload" && (
          <>
            {/* Drop zone */}
            <DropZone onFiles={handleFileUpload} />

            {/* File list */}
            {uploadedFiles.length > 0 && (
              <div className="flex flex-col gap-2">
                <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-widest">
                  Hochgeladene Dateien
                </h2>
                {uploadedFiles.map((f, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-3 rounded-lg bg-surface border border-border px-4 py-3 text-sm"
                  >
                    <FileIcon />
                    <span className="text-foreground">{f.filename}</span>
                    <span className="text-xs text-muted ml-auto">
                      {f.extracted_text.length} Zeichen extrahiert
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Consent checkbox — only shown when files are uploaded */}
            {uploadedFiles.length > 0 && (
              <label className="flex items-start gap-3 cursor-pointer rounded-lg border border-border px-4 py-3 bg-surface hover:border-accent transition-colors">
                <input
                  type="checkbox"
                  checked={consentChecked}
                  onChange={(e) => setConsentChecked(e.target.checked)}
                  className="mt-0.5 accent-accent h-4 w-4 shrink-0"
                />
                <span className="text-sm text-muted-foreground">
                  Ich erteile die Einwilligung, dass die hochgeladenen Unterlagen
                  für die Gesprächsführung und Berichterstellung verwendet werden.
                </span>
              </label>
            )}

            {/* Action buttons */}
            <div className="flex gap-3">
              <button
                onClick={() => setPhase("chat")}
                className="px-5 py-2.5 rounded-lg border border-border text-sm text-muted-foreground hover:text-foreground hover:border-border-strong transition-colors"
              >
                Ohne Unterlagen starten
              </button>
              {uploadedFiles.length > 0 && (
                <button
                  onClick={handleConsentAndProceed}
                  disabled={!consentChecked}
                  className="px-5 py-2.5 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors btn-accent-glow disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Mit Einwilligung fortfahren →
                </button>
              )}
            </div>
          </>
        )}

        {/* ── Phase: Generating ──────────────────────────────────── */}
        {activeModule === "report" && phase === "generating" && (
          <div className="flex-1 flex flex-col items-center justify-center gap-4">
            <Spinner />
            <p className="text-sm text-muted-foreground">
              Bericht wird generiert… Dies kann einen Moment dauern.
            </p>
          </div>
        )}

        {/* ── Phase: Preview ─────────────────────────────────────── */}
        {activeModule === "report" && phase === "preview" && report && (
          <>
            <div className="flex flex-col gap-2 print:hidden">
              <div className="flex items-center justify-between">
                <h1 className="text-xl font-semibold tracking-tight">
                  Generierter Bericht
                </h1>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPhase("chat")}
                    className="text-sm text-muted-foreground hover:text-foreground"
                  >
                    ← Zurück
                  </button>
                  <button
                    onClick={() => window.print()}
                    className="px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors"
                  >
                    Drucken / PDF
                  </button>
                </div>
              </div>
              <div className="flex gap-4">
                {savedReportId && (
                  <Link
                    href={`/berichte/${savedReportId}`}
                    className="text-sm text-muted-foreground hover:underline"
                  >
                    Bericht dauerhaft ansehen →
                  </Link>
                )}
                <Link
                  href="/berichte"
                  className="text-sm text-muted-foreground hover:underline"
                >
                  Alle Berichte
                </Link>
              </div>
            </div>
            <ReportPreview report={report} />
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-border px-6 py-4 text-center text-xs text-muted print:hidden">
        Logopädie Report Agent · Groq API · FastAPI + Next.js
      </footer>

      <ResetConfirmDialog
        isOpen={isResetDialogOpen}
        onClose={() => setIsResetDialogOpen(false)}
        onSoftReset={handleSoftReset}
        onFullReset={handleFullReset}
        isSending={isSending}
      />

      {showOnboarding && (
        <OnboardingOverlay onComplete={handleOnboardingComplete} />
      )}
    </div>
  );
}

/* ═══════════════════════════════ Chat Bubble ═════════════════════════════════ */

function ChatBubble({ role, content }: { role: string; content: string }) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "text-white rounded-br-md"
            : "bg-surface-elevated text-foreground rounded-bl-md"
        }`}
        style={isUser ? { background: "var(--accent)" } : undefined}
      >
        {isUser ? (
          content
        ) : (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h1: ({ children }) => (
                <h1 className="text-base font-bold text-accent mb-2 mt-1">{children}</h1>
              ),
              h2: ({ children }) => (
                <h2 className="text-sm font-bold text-accent mb-1.5 mt-1">{children}</h2>
              ),
              h3: ({ children }) => (
                <h3 className="text-sm font-semibold text-foreground/90 mb-1 mt-1">{children}</h3>
              ),
              p: ({ children }) => (
                <p className="mb-2 last:mb-0">{children}</p>
              ),
              ul: ({ children }) => (
                <ul className="list-disc list-inside mb-2 space-y-0.5 pl-1">{children}</ul>
              ),
              ol: ({ children }) => (
                <ol className="list-decimal list-inside mb-2 space-y-0.5 pl-1">{children}</ol>
              ),
              li: ({ children }) => (
                <li className="text-foreground/90">{children}</li>
              ),
              strong: ({ children }) => (
                <strong className="font-semibold text-foreground">{children}</strong>
              ),
              em: ({ children }) => (
                <em className="italic text-foreground/80">{children}</em>
              ),
              code: ({ children }) => (
                <code className="bg-black/10 dark:bg-white/10 rounded px-1 py-0.5 text-xs font-mono">{children}</code>
              ),
              hr: () => (
                <hr className="my-2 border-border/50" />
              ),
            }}
          >
            {content}
          </ReactMarkdown>
        )}
      </div>
    </div>
  );
}

/* ══════════════════════════ Anamnesis Progress ══════════════════════════════ */

const ANAMNESIS_PHASES = [
  { key: "report_type", label: "Berichtstyp" },
  { key: "patient_info", label: "Patient" },
  { key: "disorder", label: "Störungsbild" },
  { key: "anamnesis", label: "Anamnese" },
  { key: "goals", label: "Verlauf" },
  { key: "summary", label: "Abschluss" },
] as const;

type AnamnesisPhaseKey = typeof ANAMNESIS_PHASES[number]["key"];

const PHASE_ORDER: AnamnesisPhaseKey[] = ANAMNESIS_PHASES.map((p) => p.key);

function AnamnesisProgress({ currentPhase }: { currentPhase: string }) {
  const currentIndex = PHASE_ORDER.indexOf(currentPhase as AnamnesisPhaseKey);

  return (
    <div className="flex items-center gap-1 flex-wrap">
      {ANAMNESIS_PHASES.map((phase, i) => {
        const isDone = currentIndex > i;
        const isActive = currentIndex === i;
        return (
          <div key={phase.key} className="flex items-center gap-1">
            {i > 0 && (
              <span className="text-muted text-xs">›</span>
            )}
            <span
              className={`text-xs px-2 py-0.5 rounded-full font-medium transition-colors ${
                isDone
                  ? "line-through opacity-50"
                  : isActive
                  ? "text-white"
                  : "text-muted-foreground"
              }`}
              style={
                isDone
                  ? { background: "var(--accent-muted)", color: "var(--accent-text)" }
                  : isActive
                  ? { background: "var(--accent)" }
                  : { background: "var(--surface-elevated)" }
              }
            >
              {isDone ? `✓ ${phase.label}` : phase.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

/* ═══════════════════════════ Quick-Reply Bubbles ════════════════════════════ */

const QUICK_REPLY_TYPES = [
  'Befundbericht',
  'Therapiebericht kurz',
  'Therapiebericht lang',
  'Abschlussbericht',
  '✏️ Sonstiges...',
] as const;

function QuickReplyBubbles({
  onSelect,
  disabled,
}: {
  onSelect: (type: string) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex flex-wrap gap-2 pl-10 pt-1">
      {QUICK_REPLY_TYPES.map((t) => {
        const isOther = t.startsWith('✏️');
        return (
          <button
            key={t}
            onClick={() => onSelect(t)}
            disabled={disabled}
            className={[
              'rounded-full border px-4 py-2 text-sm transition-all duration-150',
              'disabled:opacity-40 disabled:cursor-not-allowed',
              isOther
                ? 'border-border-strong text-muted-foreground hover:text-foreground hover:border-border-strong bg-surface'
                : 'border-accent/50 text-accent-text bg-accent-muted hover:bg-accent-muted/80',
            ].join(' ')}
          >
            {t}
          </button>
        );
      })}
    </div>
  );
}


/* ═══════════════════════════ Dictation Button ═══════════════════════════════ */

function DictationButton({
  onTranscript,
  disabled,
  apiUrl,
}: {
  onTranscript: (text: string) => void;
  disabled?: boolean;
  apiUrl: string;
}) {
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const [isPending, setIsPending] = useState(false);

  async function start() {
    audioChunksRef.current = [];
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        setIsPending(true);
        try {
          const form = new FormData();
          form.append("audio_file", blob, "dictation.webm");
          const res = await fetch(`${apiUrl}/transcribe`, {
            method: "POST",
            body: form,
          });
          if (res.ok) {
            const data = await res.json();
            if (data.transcript) onTranscript(data.transcript);
          }
        } finally {
          setIsPending(false);
        }
      };
      recorder.start();
      setIsRecording(true);
    } catch {
      // mic access denied or unavailable — silently ignore
    }
  }

  function stop() {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  }

  if (isPending) {
    return (
      <button disabled className="px-3 py-2 rounded-lg bg-surface-elevated text-foreground/40 text-sm">
        ⏳
      </button>
    );
  }

  return isRecording ? (
    <button
      onClick={stop}
      className="px-3 py-2 rounded-lg bg-red-600 text-white motion-safe:animate-pulse text-sm"
      title="Aufnahme stoppen"
    >
      <StopIcon />
    </button>
  ) : (
    <button
      onClick={start}
      disabled={disabled}
      className="px-3 py-2 rounded-lg bg-surface-elevated hover:bg-border-strong text-foreground/80 transition-colors disabled:opacity-40 text-sm"
      title="Diktieren"
    >
      <MicIcon />
    </button>
  );
}

/* ═══════════════════════════ Mode Selection Cards ═══════════════════════════ */

function ModeSelectionCards({
  onSelect,
}: {
  onSelect: (mode: "free" | "guided") => void;
}) {
  return (
    <div className="flex gap-3 pl-2 pt-2 pb-1">
      <button
        onClick={() => onSelect("free")}
        className="flex-1 rounded-xl border border-border-strong bg-surface-2 hover:bg-surface-3 hover:border-accent/60 transition-all duration-150 p-4 text-left"
      >
        <div className="text-base font-semibold text-foreground mb-1">✏️ Freitext</div>
        <div className="text-xs text-muted-foreground leading-snug">
          Tippe alles auf einmal — ich frage nur nach was fehlt
        </div>
      </button>
      <button
        onClick={() => onSelect("guided")}
        className="flex-1 rounded-xl border border-border-strong bg-surface-2 hover:bg-surface-3 hover:border-accent/60 transition-all duration-150 p-4 text-left"
      >
        <div className="text-base font-semibold text-foreground mb-1">💬 Geführtes Gespräch</div>
        <div className="text-xs text-muted-foreground leading-snug">
          Schritt für Schritt durch alle relevanten Informationen
        </div>
      </button>
    </div>
  );
}

/* ═══════════════════════════════ Free Text Input ════════════════════════════ */

const FREE_TEXT_REPORT_TYPES = [
  { key: "befundbericht", label: "Befundbericht" },
  { key: "therapiebericht_kurz", label: "Therapiebericht kurz" },
  { key: "therapiebericht_lang", label: "Therapiebericht lang" },
  { key: "abschlussbericht", label: "Abschlussbericht" },
] as const;

function FreeTextInput({
  reportType,
  onReportTypeChange,
  value,
  onChange,
  onSubmit,
  disabled,
  apiUrl,
}: {
  reportType: string;
  onReportTypeChange: (type: string) => void;
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  disabled: boolean;
  apiUrl: string;
}) {
  return (
    <div className="flex flex-col gap-3 px-2 pt-2 pb-1">
      <div className="flex flex-wrap gap-2">
        {FREE_TEXT_REPORT_TYPES.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => onReportTypeChange(key)}
            className={[
              "rounded-full border px-4 py-1.5 text-xs font-medium transition-all duration-150",
              reportType === key
                ? "border-accent bg-accent text-white"
                : "border-border-strong text-muted-foreground hover:border-accent/60 hover:text-foreground",
            ].join(" ")}
          >
            {label}
          </button>
        ))}
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        rows={8}
        placeholder="Beschreibe Patient, Diagnose, Therapieverlauf — alles was du weißt. Ich frage nur nach was fehlt."
        className="w-full rounded-lg bg-input border border-border-strong px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-1 focus:ring-accent/50"
        onKeyDown={(e) => {
          if (e.key === "Enter" && e.ctrlKey) {
            e.preventDefault();
            onSubmit();
          }
        }}
      />
      <div className="flex items-center justify-end gap-2">
        <DictationButton
          apiUrl={apiUrl}
          disabled={disabled}
          onTranscript={(text) => onChange(value ? value + " " + text : text)}
        />
        <button
          onClick={onSubmit}
          disabled={disabled || !value.trim() || !reportType}
          className="rounded-lg bg-accent px-6 py-2 text-sm font-semibold text-white hover:bg-accent/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
        >
          Analysieren →
        </button>
      </div>
    </div>
  );
}

/* ═══════════════════════════════ Drop Zone ═══════════════════════════════════ */

function DropZone({ onFiles }: { onFiles: (files: FileList) => void }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragOver(true);
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragOver(false);
        if (e.dataTransfer.files.length) onFiles(e.dataTransfer.files);
      }}
      onClick={() => inputRef.current?.click()}
      className={`flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed px-8 py-12 cursor-pointer transition-colors ${
        isDragOver
          ? "border-accent bg-accent-muted"
          : "border-border-strong bg-surface/50 hover:bg-surface"
      }`}
    >
      <UploadIcon />
      <p className="text-sm text-muted-foreground">
        Dateien hierher ziehen oder <span className="text-accent-text">durchsuchen</span>
      </p>
      <p className="text-xs text-muted">PDF, DOCX oder TXT · Max. 10 MB</p>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.txt"
        onChange={(e) => {
          if (e.target.files?.length) onFiles(e.target.files);
        }}
        className="hidden"
      />
    </div>
  );
}

/* ═══════════════════════════════ Report Preview ══════════════════════════════ */

function ReportPreview({ report }: { report: ReportData }) {
  const typeLabels: Record<string, string> = {
    befundbericht: "Befundbericht",
    therapiebericht_kurz: "Therapiebericht (kurz) – Verordnungsbericht",
    therapiebericht_lang: "Therapiebericht (lang) – Bericht auf besondere Anforderung",
    abschlussbericht: "Abschlussbericht",
  };

  return (
    <div className="rounded-lg border border-border overflow-hidden divide-y divide-border print:border-black print:divide-black print:text-black print:bg-white">
      {/* Header */}
      <div className="px-6 py-4 bg-surface print:bg-white">
        <h2 className="text-lg font-semibold print:text-black">
          {typeLabels[report.report_type] || report.report_type}
        </h2>
      </div>

      {/* Patient & Diagnose */}
      <ReportSection title="Patientendaten">
        <p><strong>Pseudonym:</strong> {report.patient.pseudonym}</p>
        <p><strong>Altersgruppe:</strong> {report.patient.age_group}</p>
        {report.patient.gender && <p><strong>Geschlecht:</strong> {report.patient.gender}</p>}
      </ReportSection>

      <ReportSection title="Diagnose">
        {report.diagnose.indikationsschluessel && (
          <p><strong>Indikationsschlüssel:</strong> {report.diagnose.indikationsschluessel}</p>
        )}
        {report.diagnose.icd_10_codes.length > 0 && (
          <p><strong>ICD-10:</strong> {report.diagnose.icd_10_codes.join(", ")}</p>
        )}
        {report.diagnose.diagnose_text && <p>{report.diagnose.diagnose_text}</p>}
      </ReportSection>

      {/* Type-specific sections */}
      {report.report_type === "befundbericht" && (
        <>
          <ReportSection title="Anamnese">{report.anamnese}</ReportSection>
          <ReportSection title="Befund">{report.befund}</ReportSection>
          <ReportSection title="Therapieindikation">{report.therapieindikation}</ReportSection>
          {report.therapieziele && report.therapieziele.length > 0 && (
            <ReportSection title="Therapieziele">
              <ul className="list-disc list-inside space-y-1">
                {report.therapieziele.map((z, i) => <li key={i}>{z}</li>)}
              </ul>
            </ReportSection>
          )}
          <ReportSection title="Empfehlung">{report.empfehlung}</ReportSection>
        </>
      )}

      {report.report_type === "therapiebericht_kurz" && (
        <ReportSection title="Empfehlungen">{report.empfehlungen}</ReportSection>
      )}

      {report.report_type === "therapiebericht_lang" && (
        <>
          <ReportSection title="Therapeutische Diagnostik">{report.therapeutische_diagnostik}</ReportSection>
          <ReportSection title="Aktueller Krankheitsstatus">{report.aktueller_krankheitsstatus}</ReportSection>
          <ReportSection title="Aktueller Therapiestand">{report.aktueller_therapiestand}</ReportSection>
          <ReportSection title="Weiteres Vorgehen">{report.weiteres_vorgehen}</ReportSection>
        </>
      )}

      {report.report_type === "abschlussbericht" && (
        <>
          <ReportSection title="Therapieverlauf">{report.therapieverlauf_zusammenfassung}</ReportSection>
          <ReportSection title="Ergebnis">{report.ergebnis}</ReportSection>
          <ReportSection title="Empfehlung">{report.empfehlung}</ReportSection>
        </>
      )}
    </div>
  );
}

function ReportSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="px-6 py-4 bg-surface/60 print:bg-white">
      <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-2 print:text-black print:font-bold print:text-sm print:normal-case">
        {title}
      </h3>
      <div className="text-sm text-foreground leading-relaxed whitespace-pre-wrap print:text-black">
        {children}
      </div>
    </div>
  );
}

/* ═══════════════════════════ Phonological Analysis View ══════════════════════ */

function PhonologicalAnalysisView({ api }: { api: string }) {
  const [wordPairs, setWordPairs] = useState<{ target: string; production: string }[]>([
    { target: "", production: "" },
  ]);
  const [childAge, setChildAge] = useState("");
  const [result, setResult] = useState<PhonologicalAnalysisData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState(0);

  const PHONOLOGY_STEPS: StepConfig[] = [
    {
      label: "Eingabe",
      infoTitle: "Wortpaare eingeben",
      infoText: "Geben Sie das Zielwort und die tatsächliche Produktion des Kindes ein. Fügen Sie beliebig viele Paare hinzu.",
    },
    {
      label: "Analyse",
      infoTitle: "Analyse läuft",
      infoText: "Die KI analysiert die phonologischen Prozesse und bewertet den Schweregrad je Wortpaar.",
    },
    {
      label: "Ergebnis",
      infoTitle: "Analyseergebnis",
      infoText: "Prüfen Sie die erkannten Prozesse und Empfehlungen. Klicken Sie auf ✓ Eingabe um neue Wortpaare zu analysieren.",
      infoVariant: "success",
    },
  ];

  function addPair() {
    setWordPairs((prev) => [...prev, { target: "", production: "" }]);
  }

  function updatePair(index: number, field: "target" | "production", value: string) {
    setWordPairs((prev) => prev.map((p, i) => (i === index ? { ...p, [field]: value } : p)));
  }

  function removePair(index: number) {
    if (wordPairs.length > 1) setWordPairs((prev) => prev.filter((_, i) => i !== index));
  }

  async function analyze() {
    const valid = wordPairs.filter((p) => p.target.trim() && p.production.trim());
    if (!valid.length) return;
    setLoading(true);
    setStep(1); // Schritt: Analyse läuft
    setError(null);
    try {
      const res = await fetch(`${api}/analysis/phonological-text?${childAge ? `child_age=${encodeURIComponent(childAge)}` : ""}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(valid),
      });
      if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail ?? "Analyse fehlgeschlagen.");
      setResult(await res.json());
      setStep(2); // Schritt: Ergebnis
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler.");
      setStep(0); // Bei Fehler zurück zu Eingabe
    } finally {
      setLoading(false);
    }
  }

  const severityColors: Record<string, string> = {
    leicht: "bg-yellow-900 text-yellow-300",
    mittel: "bg-orange-900 text-orange-300",
    schwer: "bg-red-900 text-red-300",
  };

  return (
    <>
      <WorkflowStepper
        steps={PHONOLOGY_STEPS}
        currentStep={step}
        onStepClick={step > 0 ? (i) => { setStep(i); if (i === 0) setResult(null); } : undefined}
      />
      <h1 className="text-xl font-semibold tracking-tight">Phonologische Prozessanalyse</h1>
      <p className="text-sm text-muted-foreground">
        Geben Sie Zielwörter und die tatsächliche Produktion des Kindes ein. Die KI identifiziert
        automatisch phonologische Prozesse und bewertet den Schweregrad.
      </p>

      <div className="flex items-center gap-3">
        <label className="text-sm text-muted-foreground">Alter des Kindes:</label>
        <input
          type="text"
          value={childAge}
          onChange={(e) => setChildAge(e.target.value)}
          placeholder="z.B. 4;6 Jahre"
          className="rounded-lg bg-surface border border-border-strong px-3 py-2 text-sm w-40 focus:outline-none focus:border-ring"
        />
      </div>

      <div className="flex flex-col gap-2">
        {wordPairs.map((pair, i) => (
          <div key={i} className="flex items-center gap-2">
            <input
              type="text"
              value={pair.target}
              onChange={(e) => updatePair(i, "target", e.target.value)}
              placeholder="Zielwort"
              className="flex-1 rounded-lg bg-surface border border-border-strong px-3 py-2 text-sm focus:outline-none focus:border-ring"
            />
            <span className="text-muted">→</span>
            <input
              type="text"
              value={pair.production}
              onChange={(e) => updatePair(i, "production", e.target.value)}
              placeholder="Produktion"
              className="flex-1 rounded-lg bg-surface border border-border-strong px-3 py-2 text-sm focus:outline-none focus:border-ring"
            />
            <button onClick={() => removePair(i)} className="text-muted hover:text-red-400 text-sm px-2">✕</button>
          </div>
        ))}
        <button onClick={addPair} className="self-start text-sm text-accent-text hover:text-accent-text">+ Weiteres Wortpaar</button>
      </div>

      <button
        onClick={analyze}
        disabled={loading}
        className="self-start px-6 py-3 rounded-lg bg-accent hover:bg-accent-hover text-white font-medium text-sm transition-colors disabled:opacity-40"
      >
        {loading ? "Analysiere…" : "Analyse starten"}
      </button>

      {error && <div className="rounded-lg bg-red-950 border border-red-800 px-5 py-4 text-sm text-red-300">{error}</div>}

      {result && (
        <div className="flex flex-col gap-4">
          {/* Results table */}
          <div className="rounded-lg border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-surface text-muted-foreground text-xs uppercase tracking-wider">
                  <th className="px-4 py-3 text-left">Zielwort</th>
                  <th className="px-4 py-3 text-left">Produktion</th>
                  <th className="px-4 py-3 text-left">Prozesse</th>
                  <th className="px-4 py-3 text-left">Schwere</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {result.items.map((item, i) => (
                  <tr key={i} className="bg-surface/60">
                    <td className="px-4 py-3 font-mono">{item.target_word}</td>
                    <td className="px-4 py-3 font-mono text-red-300">{item.production}</td>
                    <td className="px-4 py-3">
                      <ul className="space-y-1">
                        {item.processes.map((p, j) => (
                          <li key={j} className="text-xs text-foreground/80">{p}</li>
                        ))}
                      </ul>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-1 rounded-full ${severityColors[item.severity] || "bg-surface-elevated text-muted-foreground"}`}>
                        {item.severity}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Summary */}
          <div className="rounded-lg border border-border bg-surface/60 px-5 py-4">
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-2">Zusammenfassung</h3>
            <p className="text-sm text-foreground whitespace-pre-wrap">{result.summary}</p>
            <div className="mt-3 flex items-center gap-2">
              <span className={`text-xs px-2 py-1 rounded-full ${result.age_appropriate ? "bg-green-900 text-green-300" : "bg-red-900 text-red-300"}`}>
                {result.age_appropriate ? "Altersgemäß" : "Nicht altersgemäß"}
              </span>
            </div>
            {result.recommended_focus.length > 0 && (
              <div className="mt-3">
                <h4 className="text-xs text-muted-foreground mb-1">Empfohlene Therapieschwerpunkte:</h4>
                <ul className="space-y-1">
                  {result.recommended_focus.map((f, i) => (
                    <li key={i} className="text-sm text-accent-text flex items-start gap-2">
                      <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-accent shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}

/* ═══════════════════════════ Therapy Plan View ═══════════════════════════════ */

type TpMode = "select" | "chat" | "from-report" | "generating" | "plan";

interface SavedReportSummary {
  id: number;
  pseudonym: string;
  report_type: string;
  created_at: string;
}

interface SavedPlanSummary {
  id: number;
  created_at: string;
  patient_pseudonym: string;
  report_id: number | null;
}

const THERAPY_PLAN_STEPS: StepConfig[] = [
  {
    label: "Eingabe",
    infoTitle: "Patienten auswählen oder Daten eingeben",
    infoText:
      "Starten Sie einen Mini-Chat für einen neuen Patienten oder wählen Sie einen gespeicherten Bericht als Grundlage.",
  },
  {
    label: "Generieren",
    infoTitle: "Therapieplan wird generiert",
    infoText: "Der KI-Assistent erstellt jetzt einen ICF-basierten Therapieplan. Dies dauert wenige Sekunden.",
  },
  {
    label: "Plan",
    infoTitle: "Therapieplan fertig",
    infoText:
      "Prüfen und bearbeiten Sie den Therapieplan. Klicken Sie auf ✓ Eingabe um neu zu starten.",
    infoVariant: "success",
  },
];

function TherapyPlanView({ api, sessionId: _sessionId }: { api: string; sessionId: string | null }) {
  const [tpMode, setTpMode] = useState<TpMode>("select");
  const [tpSessionId, setTpSessionId] = useState<string | null>(null);
  const [tpReportId, setTpReportId] = useState<number | null>(null);
  const [tpMessages, setTpMessages] = useState<ChatMsg[]>([]);
  const [tpInput, setTpInput] = useState("");
  const [tpIsSending, setTpIsSending] = useState(false);
  const [tpIsComplete, setTpIsComplete] = useState(false);
  const [plan, setPlan] = useState<TherapyPlanData | null>(null);
  const [tpSavedId, setTpSavedId] = useState<number | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState<TherapyPlanData | null>(null);
  const [savedPlans, setSavedPlans] = useState<SavedPlanSummary[]>([]);
  const [savedReports, setSavedReports] = useState<SavedReportSummary[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const tpChatEndRef = useRef<HTMLDivElement>(null);

  const stepIndex = tpMode === "select" || tpMode === "chat" || tpMode === "from-report" ? 0
    : tpMode === "generating" ? 1
    : 2;

  // Load saved plans and reports on mount
  useEffect(() => {
    fetch(`${api}/therapy-plans`)
      .then((r) => r.ok ? r.json() : [])
      .then(setSavedPlans)
      .catch(() => {});
    fetch(`${api}/reports`)
      .then((r) => r.ok ? r.json() : [])
      .then(setSavedReports)
      .catch(() => {});
  }, [api]);

  // Auto-scroll mini-chat
  useEffect(() => {
    tpChatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [tpMessages]);

  async function startMiniChat() {
    setError(null);
    try {
      const res = await fetch(`${api}/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: "therapy_plan" }),
      });
      if (!res.ok) throw new Error("Session konnte nicht erstellt werden.");
      const data = await res.json();
      setTpSessionId(data.session_id);
      const greeting = data.collected_data?.greeting ?? "Guten Tag! Für welchen Patienten möchten Sie einen Therapieplan erstellen?";
      setTpMessages([{ role: "assistant", content: greeting }]);
      setTpMode("chat");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler.");
    }
  }

  async function sendTpMessage() {
    if (!tpInput.trim() || !tpSessionId || tpIsSending) return;
    const msg = tpInput.trim();
    setTpInput("");
    setTpMessages((prev) => [...prev, { role: "user", content: msg }]);
    setTpIsSending(true);
    setError(null);
    try {
      const res = await fetch(`${api}/sessions/${tpSessionId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg }),
      });
      if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail ?? "Fehler.");
      const data: ChatResponse = await res.json();
      setTpMessages((prev) => [...prev, { role: "assistant", content: data.message }]);
      if (data.is_anamnesis_complete) setTpIsComplete(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler.");
    } finally {
      setTpIsSending(false);
    }
  }

  async function generateFromSession(sid: string, rid?: number) {
    setTpMode("generating");
    setError(null);
    try {
      const res = await fetch(`${api}/sessions/${sid}/therapy-plan`, { method: "POST" });
      if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail ?? "Plan-Generierung fehlgeschlagen.");
      const p = await res.json();
      setPlan(p);
      if (rid) setTpReportId(rid);
      setTpMode("plan");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler.");
      setTpMode(tpSessionId ? "chat" : "from-report");
    }
  }

  async function generateFromReport() {
    const rid = parseInt(selectedReportId);
    if (!rid) return;
    // Create a temporary session for plan generation using report context
    setError(null);
    try {
      const sessionRes = await fetch(`${api}/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: "anamnesis" }),
      });
      if (!sessionRes.ok) throw new Error("Session konnte nicht erstellt werden.");
      const sessionData = await sessionRes.json();
      const sid = sessionData.session_id;
      setTpSessionId(sid);
      await generateFromSession(sid, rid);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler.");
    }
  }

  async function savePlan() {
    if (!plan || !tpSessionId) return;
    setIsSaving(true);
    setError(null);
    try {
      const res = await fetch(`${api}/therapy-plans`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: tpSessionId,
          plan_data: plan,
          report_id: tpReportId ?? null,
        }),
      });
      if (!res.ok) throw new Error("Fehler beim Speichern.");
      const saved: SavedPlanSummary = await res.json();
      setTpSavedId(saved.id);
      setSavedPlans((prev) => [saved, ...prev]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler.");
    } finally {
      setIsSaving(false);
    }
  }

  async function saveEditedPlan() {
    if (!editData || !tpSavedId) return;
    setIsSaving(true);
    setError(null);
    try {
      const res = await fetch(`${api}/therapy-plans/${tpSavedId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editData),
      });
      if (!res.ok) throw new Error("Fehler beim Speichern.");
      setPlan(editData);
      setIsEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler.");
    } finally {
      setIsSaving(false);
    }
  }

  async function loadSavedPlan(id: number) {
    setError(null);
    try {
      const res = await fetch(`${api}/therapy-plans/${id}`);
      if (!res.ok) throw new Error("Plan nicht gefunden.");
      const data = await res.json();
      setPlan(data as TherapyPlanData);
      setTpSavedId(data._db_id ?? id);
      setTpMode("plan");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler.");
    }
  }

  function resetToSelect() {
    setTpMode("select");
    setTpSessionId(null);
    setTpReportId(null);
    setTpMessages([]);
    setTpIsComplete(false);
    setPlan(null);
    setTpSavedId(null);
    setIsEditing(false);
    setEditData(null);
    setError(null);
    setSelectedReportId("");
  }

  const REPORT_TYPE_LABELS: Record<string, string> = {
    befundbericht: "Befundbericht",
    therapiebericht_kurz: "Therapiebericht (kurz)",
    therapiebericht_lang: "Therapiebericht (lang)",
    abschlussbericht: "Abschlussbericht",
  };

  return (
    <>
      <WorkflowStepper
        steps={THERAPY_PLAN_STEPS}
        currentStep={stepIndex}
        onStepClick={stepIndex > 0 ? (i) => { if (i === 0) resetToSelect(); } : undefined}
      />

      <h1 className="text-xl font-semibold tracking-tight">KI-gestützter Therapieplan</h1>

      {error && (
        <div className="rounded-lg bg-red-950 border border-red-800 px-5 py-4 text-sm text-red-300">{error}</div>
      )}

      {/* ── Select mode ── */}
      {tpMode === "select" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <button
              onClick={startMiniChat}
              className="flex flex-col gap-2 rounded-lg border border-border bg-surface px-5 py-4 text-left hover:border-accent transition-colors"
            >
              <span className="text-sm font-semibold text-foreground">Neu (Mini-Chat)</span>
              <span className="text-xs text-muted-foreground">
                Kurzes Gespräch (4 Fragen) für einen neuen Patienten — ohne vorherige Anamnese.
              </span>
            </button>
            <button
              onClick={() => setTpMode("from-report")}
              className="flex flex-col gap-2 rounded-lg border border-border bg-surface px-5 py-4 text-left hover:border-accent transition-colors"
            >
              <span className="text-sm font-semibold text-foreground">Aus Bericht</span>
              <span className="text-xs text-muted-foreground">
                Therapieplan auf Basis eines bereits gespeicherten Berichts erstellen.
              </span>
            </button>
          </div>

          {savedPlans.length > 0 && (
            <div>
              <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-2">
                Gespeicherte Therapiepläne
              </h2>
              <div className="rounded-lg border border-border divide-y divide-border overflow-hidden">
                {savedPlans.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => loadSavedPlan(p.id)}
                    className="w-full flex items-center justify-between px-4 py-3 bg-surface hover:bg-surface-elevated text-left transition-colors"
                  >
                    <div>
                      <p className="text-sm font-medium text-foreground">{p.patient_pseudonym}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(p.created_at).toLocaleDateString("de-DE")}
                        {p.report_id ? ` · Bericht #${p.report_id}` : ""}
                      </p>
                    </div>
                    <span className="text-xs text-accent">Laden →</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Mini-chat mode ── */}
      {tpMode === "chat" && (
        <div className="space-y-4">
          <div className="rounded-lg border border-border bg-surface min-h-[200px] max-h-[380px] overflow-y-auto p-4 space-y-3">
            {tpMessages.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`rounded-lg px-4 py-2 text-sm max-w-[80%] whitespace-pre-wrap ${
                    m.role === "user"
                      ? "bg-accent text-white"
                      : "bg-surface-elevated text-foreground"
                  }`}
                >
                  {m.content}
                </div>
              </div>
            ))}
            {tpIsSending && (
              <div className="flex justify-start">
                <div className="rounded-lg px-4 py-2 text-sm bg-surface-elevated text-muted-foreground">…</div>
              </div>
            )}
            <div ref={tpChatEndRef} />
          </div>

          {!tpIsComplete ? (
            <div className="flex gap-2">
              <input
                type="text"
                value={tpInput}
                onChange={(e) => setTpInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendTpMessage()}
                placeholder="Ihre Antwort…"
                disabled={tpIsSending}
                className="flex-1 rounded-lg border border-border bg-surface px-4 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-accent disabled:opacity-40"
              />
              <button
                onClick={sendTpMessage}
                disabled={tpIsSending || !tpInput.trim()}
                className="px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors disabled:opacity-40"
              >
                Senden
              </button>
            </div>
          ) : (
            <button
              onClick={() => tpSessionId && generateFromSession(tpSessionId)}
              className="self-start px-6 py-3 rounded-lg bg-accent hover:bg-accent-hover text-white font-medium text-sm transition-colors"
            >
              Therapieplan generieren
            </button>
          )}
        </div>
      )}

      {/* ── From-report mode ── */}
      {tpMode === "from-report" && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Wählen Sie einen gespeicherten Bericht als Grundlage für den Therapieplan.
          </p>
          {savedReports.length === 0 ? (
            <p className="text-sm text-muted-foreground italic">Keine gespeicherten Berichte gefunden.</p>
          ) : (
            <div className="flex gap-3 items-center">
              <select
                value={selectedReportId}
                onChange={(e) => setSelectedReportId(e.target.value)}
                className="flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
              >
                <option value="">— Bericht auswählen —</option>
                {savedReports.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.pseudonym} · {REPORT_TYPE_LABELS[r.report_type] ?? r.report_type} ·{" "}
                    {new Date(r.created_at).toLocaleDateString("de-DE")}
                  </option>
                ))}
              </select>
              <button
                onClick={generateFromReport}
                disabled={!selectedReportId}
                className="px-5 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors disabled:opacity-40"
              >
                Generieren
              </button>
            </div>
          )}
          <button
            onClick={() => setTpMode("select")}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            ← Zurück
          </button>
        </div>
      )}

      {/* ── Generating mode ── */}
      {tpMode === "generating" && (
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <div className="w-4 h-4 rounded-full border-2 border-accent border-t-transparent animate-spin" />
          Therapieplan wird generiert…
        </div>
      )}

      {/* ── Plan mode ── */}
      {tpMode === "plan" && plan && (
        <div className="space-y-4">
          <div className="rounded-lg border border-border overflow-hidden divide-y divide-border print:border-black print:text-black print:bg-white">
            {/* Header */}
            <div className="px-6 py-4 bg-surface print:bg-white">
              {isEditing ? (
                <div className="space-y-2">
                  <input
                    value={editData?.patient_pseudonym ?? ""}
                    onChange={(e) => setEditData((d) => d ? { ...d, patient_pseudonym: e.target.value } : d)}
                    className="w-full rounded border border-border bg-surface-elevated px-3 py-1.5 text-sm font-semibold text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
                    placeholder="Patient (Pseudonym)"
                  />
                  <textarea
                    value={editData?.diagnose_text ?? ""}
                    onChange={(e) => setEditData((d) => d ? { ...d, diagnose_text: e.target.value } : d)}
                    rows={2}
                    className="w-full rounded border border-border bg-surface-elevated px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-accent resize-none"
                    placeholder="Diagnose"
                  />
                  <div className="flex gap-3">
                    <input
                      value={editData?.frequency ?? ""}
                      onChange={(e) => setEditData((d) => d ? { ...d, frequency: e.target.value } : d)}
                      className="flex-1 rounded border border-border bg-surface-elevated px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
                      placeholder="Frequenz"
                    />
                    <input
                      type="number"
                      value={editData?.total_sessions ?? 0}
                      onChange={(e) => setEditData((d) => d ? { ...d, total_sessions: parseInt(e.target.value) || 0 } : d)}
                      className="w-28 rounded border border-border bg-surface-elevated px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
                      placeholder="Sitzungen"
                    />
                  </div>
                </div>
              ) : (
                <>
                  <h2 className="text-lg font-semibold">Therapieplan: {plan.patient_pseudonym}</h2>
                  <p className="text-sm text-muted-foreground mt-1">{plan.diagnose_text}</p>
                  <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                    <span>Frequenz: {plan.frequency}</span>
                    <span>Gesamt: {plan.total_sessions} Sitzungen</span>
                  </div>
                </>
              )}
            </div>

            {/* Phases */}
            {(isEditing ? editData?.plan_phases : plan.plan_phases)?.map((phase, pi) => (
              <div key={pi} className="px-6 py-4 bg-surface/60">
                <h3 className="text-sm font-semibold text-accent-text mb-3">
                  {isEditing ? (
                    <input
                      value={phase.phase_name}
                      onChange={(e) => setEditData((d) => {
                        if (!d) return d;
                        const phases = [...d.plan_phases];
                        phases[pi] = { ...phases[pi], phase_name: e.target.value };
                        return { ...d, plan_phases: phases };
                      })}
                      className="rounded border border-border bg-surface-elevated px-2 py-0.5 text-sm font-semibold text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
                    />
                  ) : (
                    <>Phase {pi + 1}: {phase.phase_name}</>
                  )}
                  <span className="text-xs text-muted-foreground font-normal ml-2">{phase.duration}</span>
                </h3>
                <div className="space-y-4">
                  {phase.goals.map((goal, gi) => (
                    <div key={gi} className="rounded-lg bg-surface-elevated/50 p-4">
                      <div className="flex items-start gap-2 mb-2">
                        <span className="text-xs px-2 py-0.5 rounded bg-accent-muted text-accent-text shrink-0 font-mono">
                          {goal.icf_code}
                        </span>
                        {isEditing ? (
                          <textarea
                            value={goal.goal_text}
                            onChange={(e) => setEditData((d) => {
                              if (!d) return d;
                              const phases = [...d.plan_phases];
                              const goals = [...phases[pi].goals];
                              goals[gi] = { ...goals[gi], goal_text: e.target.value };
                              phases[pi] = { ...phases[pi], goals };
                              return { ...d, plan_phases: phases };
                            })}
                            rows={2}
                            className="flex-1 rounded border border-border bg-surface-elevated px-2 py-1 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-accent resize-none"
                          />
                        ) : (
                          <span className="text-sm text-foreground">{goal.goal_text}</span>
                        )}
                      </div>
                      <div className="ml-4 space-y-2 text-xs">
                        <div>
                          <span className="text-muted-foreground">Methoden: </span>
                          {isEditing ? (
                            <input
                              value={goal.methods.join(", ")}
                              onChange={(e) => setEditData((d) => {
                                if (!d) return d;
                                const phases = [...d.plan_phases];
                                const goals = [...phases[pi].goals];
                                goals[gi] = { ...goals[gi], methods: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) };
                                phases[pi] = { ...phases[pi], goals };
                                return { ...d, plan_phases: phases };
                              })}
                              className="rounded border border-border bg-surface-elevated px-2 py-0.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-accent w-full mt-0.5"
                              placeholder="Methode 1, Methode 2, …"
                            />
                          ) : (
                            <span className="text-foreground/80">{goal.methods.join(", ")}</span>
                          )}
                        </div>
                        <div>
                          <span className="text-muted-foreground">Meilensteine: </span>
                          <span className="text-foreground/80">{goal.milestones.join(" → ")}</span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Zeitrahmen: </span>
                          <span className="text-foreground/80">{goal.timeframe}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}

            {/* Elternberatung */}
            {(isEditing ? editData?.elternberatung : plan.elternberatung) && (
              <div className="px-6 py-4 bg-surface/60">
                <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-2">Elternberatung</h3>
                {isEditing ? (
                  <textarea
                    value={editData?.elternberatung ?? ""}
                    onChange={(e) => setEditData((d) => d ? { ...d, elternberatung: e.target.value } : d)}
                    rows={3}
                    className="w-full rounded border border-border bg-surface-elevated px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-accent resize-none"
                  />
                ) : (
                  <p className="text-sm text-foreground whitespace-pre-wrap">{plan.elternberatung}</p>
                )}
              </div>
            )}

            {/* Häusliche Übungen */}
            {plan.haeusliche_uebungen.length > 0 && (
              <div className="px-6 py-4 bg-surface/60">
                <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-2">Häusliche Übungen</h3>
                <ul className="space-y-1">
                  {plan.haeusliche_uebungen.map((u, i) => (
                    <li key={i} className="text-sm text-foreground flex items-start gap-2">
                      <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-accent shrink-0" />
                      {u}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Action bar */}
            <div className="px-6 py-3 bg-surface flex items-center justify-between gap-3 print:hidden flex-wrap">
              <div className="flex gap-2">
                {isEditing ? (
                  <>
                    <button
                      onClick={saveEditedPlan}
                      disabled={isSaving || !tpSavedId}
                      className="px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors disabled:opacity-40"
                    >
                      {isSaving ? "Speichert…" : "Speichern"}
                    </button>
                    <button
                      onClick={() => { setIsEditing(false); setEditData(null); }}
                      className="px-4 py-2 rounded-lg border border-border text-sm text-muted-foreground hover:text-foreground transition-colors"
                    >
                      Abbrechen
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => { setIsEditing(true); setEditData(JSON.parse(JSON.stringify(plan))); }}
                    className="px-4 py-2 rounded-lg border border-border text-sm text-foreground hover:border-accent transition-colors"
                  >
                    Editieren
                  </button>
                )}
              </div>
              <div className="flex gap-2">
                {!tpSavedId && (
                  <button
                    onClick={savePlan}
                    disabled={isSaving}
                    className="px-4 py-2 rounded-lg border border-accent text-accent text-sm font-medium hover:bg-accent hover:text-white transition-colors disabled:opacity-40"
                  >
                    {isSaving ? "Speichert…" : "In Datenbank speichern"}
                  </button>
                )}
                {tpSavedId && (
                  <span className="text-xs text-muted-foreground self-center">✓ Gespeichert</span>
                )}
                <button
                  onClick={() => window.print()}
                  className="px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors"
                >
                  Drucken / PDF
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/* ═══════════════════════════ Report Comparison View ══════════════════════════ */

function ReportComparisonView({ api }: { api: string }) {
  const [result, setResult] = useState<ReportComparisonData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const initialRef = useRef<HTMLInputElement>(null);
  const currentRef = useRef<HTMLInputElement>(null);
  const [step, setStep] = useState(0);

  const COMPARE_STEPS: StepConfig[] = [
    {
      label: "Upload",
      infoTitle: "Berichte hochladen",
      infoText:
        "Laden Sie den Erstbefund und den aktuellen Bericht hoch (PDF, DOCX oder TXT). Die KI analysiert die Unterschiede und erstellt einen strukturierten Fortschrittsbericht.",
    },
    {
      label: "Vergleich",
      infoTitle: "Vergleich läuft",
      infoText: "Die KI analysiert beide Berichte und identifiziert Veränderungen je Bereich.",
    },
    {
      label: "Ergebnis",
      infoTitle: "Vergleichsergebnis",
      infoText:
        "Prüfen Sie die erkannten Veränderungen und die Gesamtempfehlung. Klicken Sie auf ✓ Upload für einen neuen Vergleich.",
      infoVariant: "success",
    },
  ];

  async function compare() {
    const initialFile = initialRef.current?.files?.[0];
    const currentFile = currentRef.current?.files?.[0];
    if (!initialFile || !currentFile) {
      setError("Bitte wählen Sie beide Berichte aus.");
      return;
    }
    setLoading(true);
    setStep(1); // Schritt: Vergleich läuft
    setError(null);
    const formData = new FormData();
    formData.append("initial_report", initialFile);
    formData.append("current_report", currentFile);
    try {
      const res = await fetch(`${api}/analysis/compare`, { method: "POST", body: formData });
      if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail ?? "Vergleich fehlgeschlagen.");
      setResult(await res.json());
      setStep(2); // Schritt: Ergebnis
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler.");
      setStep(0); // Bei Fehler zurück zu Upload
    } finally {
      setLoading(false);
    }
  }

  const changeColors: Record<string, string> = {
    verbessert: "bg-green-900 text-green-300",
    "unverändert": "bg-surface-elevated text-muted-foreground",
    verschlechtert: "bg-red-900 text-red-300",
  };

  return (
    <>
      <WorkflowStepper
        steps={COMPARE_STEPS}
        currentStep={step}
        onStepClick={step > 0 ? (i) => { setStep(i); if (i === 0) setResult(null); } : undefined}
      />
      <h1 className="text-xl font-semibold tracking-tight">Vergleichende Berichtsanalyse</h1>
      <p className="text-sm text-muted-foreground">
        Laden Sie zwei Berichte hoch (z.B. Erstbefund und aktueller Befund). Die KI analysiert
        Veränderungen und erstellt einen strukturierten Fortschrittsbericht.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="flex flex-col gap-2">
          <label className="text-sm text-muted-foreground">Erstbefund / Älterer Bericht:</label>
          <input ref={initialRef} type="file" accept=".pdf,.docx,.txt" className="text-sm text-muted-foreground file:mr-3 file:rounded-lg file:border-0 file:bg-surface-elevated file:px-4 file:py-2 file:text-sm file:text-foreground/80 file:cursor-pointer" />
        </div>
        <div className="flex flex-col gap-2">
          <label className="text-sm text-muted-foreground">Aktueller Bericht:</label>
          <input ref={currentRef} type="file" accept=".pdf,.docx,.txt" className="text-sm text-muted-foreground file:mr-3 file:rounded-lg file:border-0 file:bg-surface-elevated file:px-4 file:py-2 file:text-sm file:text-foreground/80 file:cursor-pointer" />
        </div>
      </div>

      <button
        onClick={compare}
        disabled={loading}
        className="self-start px-6 py-3 rounded-lg bg-accent hover:bg-accent-hover text-white font-medium text-sm transition-colors disabled:opacity-40"
      >
        {loading ? "Vergleiche…" : "Berichte vergleichen"}
      </button>

      {error && <div className="rounded-lg bg-red-950 border border-red-800 px-5 py-4 text-sm text-red-300">{error}</div>}

      {result && (
        <div className="flex flex-col gap-4">
          {/* Comparison table */}
          <div className="rounded-lg border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-surface text-muted-foreground text-xs uppercase tracking-wider">
                  <th className="px-4 py-3 text-left">Bereich</th>
                  <th className="px-4 py-3 text-left">Erstbefund</th>
                  <th className="px-4 py-3 text-left">Aktuell</th>
                  <th className="px-4 py-3 text-left">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {result.items.map((item, i) => (
                  <tr key={i} className="bg-surface/60">
                    <td className="px-4 py-3 font-medium text-foreground/80">{item.category}</td>
                    <td className="px-4 py-3 text-muted-foreground text-xs">{item.initial_finding}</td>
                    <td className="px-4 py-3 text-foreground/80 text-xs">{item.current_finding}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-1 rounded-full ${changeColors[item.change] || "bg-surface-elevated text-muted-foreground"}`}>
                        {item.change}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Summary */}
          <div className="rounded-lg border border-border bg-surface/60 px-5 py-4 space-y-3">
            <div>
              <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-1">Gesamtfortschritt</h3>
              <p className="text-sm text-foreground whitespace-pre-wrap">{result.overall_progress}</p>
            </div>
            {result.remaining_issues.length > 0 && (
              <div>
                <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-1">Verbleibende Probleme</h3>
                <ul className="space-y-1">{result.remaining_issues.map((r, i) => (
                  <li key={i} className="text-sm text-orange-300 flex items-start gap-2">
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-orange-500 shrink-0" />{r}
                  </li>
                ))}</ul>
              </div>
            )}
            <div>
              <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-1">Empfehlung</h3>
              <p className="text-sm text-foreground whitespace-pre-wrap">{result.recommendation}</p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/* ═══════════════════════════ Text Suggestion View ════════════════════════════ */

function TextSuggestionView({ api }: { api: string }) {
  const [text, setText] = useState("");
  const [reportType, setReportType] = useState("befundbericht");
  const [disorder, setDisorder] = useState("");
  const [section, setSection] = useState("befund");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function onTextChange(val: string) {
    setText(val);
    if (timerRef.current) clearTimeout(timerRef.current);
    if (val.trim().length > 10) {
      timerRef.current = setTimeout(() => fetchSuggestions(val), 800);
    } else {
      setSuggestions([]);
    }
  }

  async function fetchSuggestions(input: string) {
    setLoading(true);
    try {
      const res = await fetch(`${api}/suggest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: input, report_type: reportType, disorder, section }),
      });
      if (!res.ok) return;
      const data = await res.json();
      setSuggestions(data.suggestions || []);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }

  function applySuggestion(s: string) {
    setText(text + s);
    setSuggestions([]);
  }

  return (
    <>
      {/* Header-Karte statt Stepper — kein linearer Schritt-Flow */}
      <div
        style={{
          borderLeft: "3px solid var(--border)",
          border: "1px solid var(--border)",
          borderLeftWidth: "3px",
          borderRadius: "0 6px 6px 0",
          padding: "10px 14px",
          background: "var(--surface)",
          marginBottom: "8px",
        }}
      >
        <p style={{ fontSize: "14px", fontWeight: "600", margin: "0 0 3px 0", color: "var(--foreground)" }}>
          ✏️ Textbausteine
        </p>
        <p style={{ fontSize: "12px", color: "var(--muted-foreground)", margin: 0, lineHeight: "1.5" }}>
          Geben Sie einen Text ein — die KI schlägt passende Formulierungen vor. Klicken Sie einen Vorschlag um ihn zu übernehmen.
        </p>
      </div>
      <h1 className="text-xl font-semibold tracking-tight">Intelligente Textbausteine</h1>
      <p className="text-sm text-muted-foreground">
        Beginnen Sie einen Satz und die KI schlägt kontextbezogene Vervollständigungen
        mit logopädischer Fachsprache vor. Klicken Sie auf einen Vorschlag zum Übernehmen.
      </p>

      {/* Context selectors */}
      <div className="flex flex-wrap gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground">Berichtstyp</label>
          <select value={reportType} onChange={(e) => setReportType(e.target.value)}
            className="rounded-lg bg-surface border border-border-strong px-3 py-2 text-sm focus:outline-none focus:border-ring">
            <option value="befundbericht">Befundbericht</option>
            <option value="therapiebericht_kurz">Therapiebericht (kurz)</option>
            <option value="therapiebericht_lang">Therapiebericht (lang)</option>
            <option value="abschlussbericht">Abschlussbericht</option>
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground">Abschnitt</label>
          <select value={section} onChange={(e) => setSection(e.target.value)}
            className="rounded-lg bg-surface border border-border-strong px-3 py-2 text-sm focus:outline-none focus:border-ring">
            <option value="anamnese">Anamnese</option>
            <option value="befund">Befund</option>
            <option value="therapieindikation">Therapieindikation</option>
            <option value="therapieverlauf">Therapieverlauf</option>
            <option value="empfehlung">Empfehlung</option>
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground">Störungsbild</label>
          <input type="text" value={disorder} onChange={(e) => setDisorder(e.target.value)}
            placeholder="z.B. SP1, ST2"
            className="rounded-lg bg-surface border border-border-strong px-3 py-2 text-sm w-32 focus:outline-none focus:border-ring" />
        </div>
      </div>

      {/* Text editor */}
      <div className="relative">
        <textarea
          value={text}
          onChange={(e) => onTextChange(e.target.value)}
          rows={8}
          placeholder="Beginnen Sie hier zu schreiben, z.B. 'Die phonologische Bewertung ergab...'"
          className="w-full rounded-lg bg-surface border border-border-strong px-4 py-3 text-sm leading-relaxed resize-y focus:outline-none focus:border-ring"
        />
        {loading && (
          <div className="absolute top-3 right-3">
            <Spinner />
          </div>
        )}
      </div>

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-widest">
            Vorschläge (klicken zum Übernehmen)
          </h3>
          {suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => applySuggestion(s)}
              className="text-left rounded-lg bg-surface border border-border hover:border-accent px-4 py-3 text-sm text-foreground/80 transition-colors"
            >
              <span className="text-muted">{text}</span>
              <span className="text-accent-text">{s}</span>
            </button>
          ))}
        </div>
      )}
    </>
  );
}

/* ═══════════════════════════════ Icons / Spinner ═════════════════════════════ */

function ChevronRight() {
  return (
    <svg className="w-3 h-3 text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
    </svg>
  );
}

function MicIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4" aria-hidden="true">
      <path d="M8.25 4.5a3.75 3.75 0 1 1 7.5 0v8.25a3.75 3.75 0 1 1-7.5 0V4.5Z" />
      <path d="M6 10.5a.75.75 0 0 1 .75.75v1.5a5.25 5.25 0 1 0 10.5 0v-1.5a.75.75 0 0 1 1.5 0v1.5a6.751 6.751 0 0 1-6 6.709v2.291h3a.75.75 0 0 1 0 1.5h-7.5a.75.75 0 0 1 0-1.5h3v-2.291a6.751 6.751 0 0 1-6-6.709v-1.5A.75.75 0 0 1 6 10.5Z" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4" aria-hidden="true">
      <path fillRule="evenodd" d="M4.5 7.5a3 3 0 0 1 3-3h9a3 3 0 0 1 3 3v9a3 3 0 0 1-3 3h-9a3 3 0 0 1-3-3v-9Z" clipRule="evenodd" />
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 shrink-0 mt-0.5 text-red-400" aria-hidden="true">
      <path fillRule="evenodd" d="M9.401 3.003c1.155-2 4.043-2 5.197 0l7.355 12.748c1.154 2-.29 4.5-2.599 4.5H4.645c-2.309 0-3.752-2.5-2.598-4.5L9.4 3.003ZM12 8.25a.75.75 0 0 1 .75.75v3.75a.75.75 0 0 1-1.5 0V9a.75.75 0 0 1 .75-.75Zm0 8.25a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z" clipRule="evenodd" />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-muted-foreground">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" />
    </svg>
  );
}

/* ══════════════════════════════════════════════════════════════════════════
   HistoryView — Bericht-Verlauf als integriertes Modul
══════════════════════════════════════════════════════════════════════════ */

const HISTORY_SECTION_LABELS: Record<string, string> = {
  anamnese: "Anamnese",
  befund: "Befund",
  therapieindikation: "Therapieindikation",
  therapieziele: "Therapieziele",
  empfehlung: "Empfehlung",
  empfehlungen: "Empfehlungen",
  therapeutische_diagnostik: "Therapeutische Diagnostik",
  aktueller_krankheitsstatus: "Aktueller Krankheitsstatus",
  aktueller_therapiestand: "Aktueller Therapiestand",
  weiteres_vorgehen: "Weiteres Vorgehen",
  therapieverlauf_zusammenfassung: "Therapieverlauf",
  ergebnis: "Ergebnis",
};

const HISTORY_SKIP_KEYS = new Set([
  "report_type", "patient", "diagnose", "_db_id", "created_at", "id", "pseudonym",
]);

function HistoryView() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<ReportDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    reportsApi.reports
      .list()
      .then(setReports)
      .catch((e: Error) => setFetchError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (selectedId === null) { setDetail(null); return; }
    setDetailLoading(true);
    reportsApi.reports
      .get(selectedId)
      .then(setDetail)
      .catch(() => setDetail(null))
      .finally(() => setDetailLoading(false));
  }, [selectedId]);

  /* ── Detail-Ansicht ── */
  if (selectedId !== null) {
    return (
      <div className="flex flex-col gap-4">
        <button
          onClick={() => setSelectedId(null)}
          className="self-start text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          ← Zurück zur Übersicht
        </button>

        {detailLoading && <p className="text-muted-foreground text-sm">Lade Bericht…</p>}

        {!detailLoading && detail && (
          <>
            <div>
              <h2 className="text-xl font-semibold">
                {REPORT_TYPE_LABELS[detail.report_type] ?? detail.report_type}
              </h2>
              <p className="text-sm text-muted-foreground mt-1">
                {detail.patient?.pseudonym ?? "Unbekannt"} ·{" "}
                {new Date(detail.created_at).toLocaleDateString("de-DE", {
                  day: "2-digit", month: "2-digit", year: "numeric",
                })}
              </p>
            </div>

            {detail.patient && (
              <section className="p-4 rounded-lg border border-border bg-card">
                <h3 className="font-medium mb-2">Patient</h3>
                <p className="text-sm">Pseudonym: {detail.patient.pseudonym}</p>
                <p className="text-sm">Altersgruppe: {detail.patient.age_group}</p>
                {detail.patient.gender && <p className="text-sm">Geschlecht: {detail.patient.gender}</p>}
              </section>
            )}

            {detail.diagnose && (detail.diagnose.diagnose_text || detail.diagnose.icd_10_codes?.length > 0) && (
              <section className="p-4 rounded-lg border border-border bg-card">
                <h3 className="font-medium mb-2">Diagnose</h3>
                {detail.diagnose.diagnose_text && <p className="text-sm">{detail.diagnose.diagnose_text}</p>}
                {detail.diagnose.indikationsschluessel && (
                  <p className="text-sm text-muted-foreground mt-1">
                    Indikationsschlüssel: {detail.diagnose.indikationsschluessel}
                  </p>
                )}
                {detail.diagnose.icd_10_codes?.length > 0 && (
                  <p className="text-sm text-muted-foreground mt-1">
                    ICD-10: {detail.diagnose.icd_10_codes.join(", ")}
                  </p>
                )}
              </section>
            )}

            {Object.entries(detail)
              .filter(([key, value]) => !HISTORY_SKIP_KEYS.has(key) && value)
              .map(([key, value]) => {
                const label = HISTORY_SECTION_LABELS[key] ?? key;
                if (Array.isArray(value)) {
                  return (
                    <section key={key} className="p-4 rounded-lg border border-border bg-card">
                      <h3 className="font-medium mb-2">{label}</h3>
                      <ul className="list-disc pl-4 space-y-1">
                        {(value as string[]).map((item, i) => (
                          <li key={i} className="text-sm">{item}</li>
                        ))}
                      </ul>
                    </section>
                  );
                }
                return (
                  <section key={key} className="p-4 rounded-lg border border-border bg-card">
                    <h3 className="font-medium mb-2">{label}</h3>
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{String(value)}</ReactMarkdown>
                    </div>
                  </section>
                );
              })}
          </>
        )}
      </div>
    );
  }

  /* ── Listen-Ansicht ── */
  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-xl font-semibold tracking-tight">Gespeicherte Berichte</h2>

      {loading && <p className="text-muted-foreground text-sm">Lade Berichte…</p>}

      {fetchError && <p className="text-destructive text-sm">Fehler: {fetchError}</p>}

      {!loading && !fetchError && reports.length === 0 && (
        <p className="text-muted-foreground text-sm">
          Noch keine Berichte gespeichert. Erstelle deinen ersten Bericht im Tab &quot;Berichterstellung&quot;.
        </p>
      )}

      {!loading && !fetchError && reports.length > 0 && (
        <ul className="space-y-2">
          {reports.map((r) => (
            <li key={r.id}>
              <button
                onClick={() => setSelectedId(r.id)}
                className="w-full flex items-center justify-between p-4 rounded-lg border border-border bg-card hover:bg-accent transition-colors text-left"
              >
                <div>
                  <span className="font-medium">{r.pseudonym}</span>
                  <span className="ml-3 text-sm text-muted-foreground">
                    {REPORT_TYPE_LABELS[r.report_type] ?? r.report_type}
                  </span>
                </div>
                <span className="text-sm text-muted-foreground">
                  {new Date(r.created_at).toLocaleDateString("de-DE", {
                    day: "2-digit", month: "2-digit", year: "numeric",
                  })}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function FileIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4 text-muted-foreground">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
    </svg>
  );
}

function Spinner() {
  return (
    <svg className="w-4 h-4 motion-safe:animate-spin text-accent-text shrink-0" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4Z" />
    </svg>
  );
}
