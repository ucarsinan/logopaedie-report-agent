"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { ChatMsg, UploadedFile, ReportData, AppPhase } from "@/types";
import { WorkflowStepper } from "@/components/WorkflowStepper";
import type { StepConfig } from "@/components/WorkflowStepper";
import { ChatView } from "./components/ChatView";
import { PreUploadView } from "./components/PreUploadView";
import { GeneratingView } from "./components/GeneratingView";
import { ReportPreview } from "./components/ReportPreview";

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
      "Prüfen Sie den generierten Bericht. Klicken Sie auf abgeschlossene Schritte (\u2713) um zurückzunavigieren — Ihre Daten bleiben erhalten.",
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

interface ReportModuleProps {
  sessionId: string | null;
  setSessionId: (id: string | null) => void;
  messages: ChatMsg[];
  setMessages: React.Dispatch<React.SetStateAction<ChatMsg[]>>;
  error: string | null;
  setError: React.Dispatch<React.SetStateAction<string | null>>;
  isSending: boolean;
  setIsSending: React.Dispatch<React.SetStateAction<boolean>>;
  onRequestReset: () => void;
}

export function ReportModule({
  sessionId,
  setSessionId,
  messages,
  setMessages,
  setError,
  isSending,
  setIsSending,
  onRequestReset,
}: ReportModuleProps) {
  const [phase, setPhase] = useState<AppPhase>("pre-upload");
  const [isAnamnesisComplete, setIsAnamnesisComplete] = useState(false);
  const [collectedFields, setCollectedFields] = useState<string[]>([]);
  const [missingFields, setMissingFields] = useState<string[]>([]);
  const [currentPhase, setCurrentPhase] = useState("greeting");
  const [inputMode, setInputMode] = useState<"select" | "free" | "guided">("select");
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [report, setReport] = useState<ReportData | null>(null);
  const [savedReportId, setSavedReportId] = useState<number | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const [consentChecked, setConsentChecked] = useState(false);

  // Restore session on mount
  useEffect(() => {
    async function init() {
      try {
        const storedId = localStorage.getItem(SESSION_STORAGE_KEY);
        if (storedId) {
          try {
            const data = await api.sessions.get(storedId);
            setSessionId(data.session_id);
            if (data.chat_history?.length) {
              setMessages(
                data.chat_history.map((m) => ({
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
            if (data.collected_data?.missing_fields) {
              setMissingFields(data.collected_data.missing_fields);
            }
            if (data.materials_consent) {
              setConsentChecked(true);
            }
            setPhase("chat");
            return;
          } catch {
            localStorage.removeItem(SESSION_STORAGE_KEY);
          }
        }

        const data = await api.sessions.create();
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // File upload
  async function handleFileUpload(files: FileList) {
    if (!sessionId) return;
    setError(null);
    for (const file of Array.from(files)) {
      try {
        const data = await api.sessions.upload(sessionId, file);
        setUploadedFiles((prev) => [...prev, data]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload fehlgeschlagen.");
      }
    }
  }

  // Consent and proceed
  async function handleConsentAndProceed() {
    if (!sessionId) return;
    try {
      await api.sessions.consent(sessionId, true);
    } catch (err) {
      setError(
        err instanceof Error
          ? `Einwilligung konnte nicht gespeichert werden: ${err.message}`
          : "Einwilligung konnte nicht gespeichert werden.",
      );
      return;
    }
    setPhase("chat");
  }

  // Generate report
  const generateReport = useCallback(async () => {
    if (!sessionId) return;
    setPhase("generating");
    setError(null);
    try {
      const data = await api.sessions.generate(sessionId);
      setReport(data);
      if (data._db_id) {
        setSavedReportId(data._db_id);
        setSavedAt(Date.now());
      }
      setPhase("preview");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unbekannter Fehler.");
      setPhase("chat");
    }
  }, [sessionId, setError]);

  // Expose reset handler — called by parent
  // Reset internal state when parent signals reset
  const handleReset = useCallback(() => {
    setPhase("pre-upload");
    setIsAnamnesisComplete(false);
    setCollectedFields([]);
    setMissingFields([]);
    setCurrentPhase("greeting");
    setInputMode("select");
    setUploadedFiles([]);
    setConsentChecked(false);
    setReport(null);
    setSavedReportId(null);
    setSavedAt(null);
  }, []);

  // Allow parent to trigger reset via onRequestReset
  useEffect(() => {
    // Store handleReset on the window so page.tsx can call it
    // This is a pragmatic bridge during the refactoring
    (window as unknown as Record<string, unknown>).__reportModuleReset = handleReset;
    return () => {
      delete (window as unknown as Record<string, unknown>).__reportModuleReset;
    };
  }, [handleReset]);

  return (
    <>
      <WorkflowStepper
        steps={REPORT_STEPS}
        currentStep={PHASE_TO_STEP[phase] ?? 0}
        onStepClick={phase !== "generating" ? (i) => setPhase(STEP_TO_PHASE[i]) : undefined}
      />

      {/* Pre-Upload phase */}
      {phase === "pre-upload" && (
        <PreUploadView
          uploadedFiles={uploadedFiles}
          consentChecked={consentChecked}
          onConsentChange={setConsentChecked}
          onFiles={handleFileUpload}
          onSkip={() => setPhase("chat")}
          onProceed={handleConsentAndProceed}
        />
      )}

      {/* Chat phase */}
      {phase === "chat" && (
        <ChatView
          sessionId={sessionId}
          messages={messages}
          setMessages={setMessages}
          isSending={isSending}
          setIsSending={setIsSending}
          isAnamnesisComplete={isAnamnesisComplete}
          setIsAnamnesisComplete={setIsAnamnesisComplete}
          collectedFields={collectedFields}
          setCollectedFields={setCollectedFields}
          missingFields={missingFields}
          setMissingFields={setMissingFields}
          currentPhase={currentPhase}
          setCurrentPhase={setCurrentPhase}
          inputMode={inputMode}
          setInputMode={setInputMode}
          setError={setError}
          onGenerateReport={generateReport}
          onRequestReset={onRequestReset}
        />
      )}

      {/* Generating phase */}
      {phase === "generating" && <GeneratingView />}

      {/* Preview phase */}
      {phase === "preview" && report && (
        <>
          <div className="flex flex-col gap-3 print:hidden">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex flex-col gap-1">
                <h1 className="text-xl font-semibold tracking-tight">
                  Generierter Bericht
                </h1>
                {savedReportId && (
                  <span
                    className="inline-flex items-center gap-1.5 text-xs text-emerald-600 dark:text-emerald-400"
                    role="status"
                    aria-live="polite"
                  >
                    <svg
                      className="size-3.5"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                      <path d="m9 11 3 3L22 4" />
                    </svg>
                    Gespeichert
                    {savedAt && (
                      <span className="text-muted-foreground">
                        {"\u00b7 "}
                        {new Date(savedAt).toLocaleTimeString("de-DE", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    )}
                  </span>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Link
                  href="/module/history"
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-surface transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                >
                  Alle Berichte
                </Link>
                <button
                  onClick={() => window.print()}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-border text-sm font-medium text-foreground hover:bg-surface transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                >
                  <svg
                    className="size-4"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <polyline points="6 9 6 2 18 2 18 9" />
                    <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
                    <rect x="6" y="14" width="12" height="8" />
                  </svg>
                  Drucken / PDF
                </button>
                <button
                  onClick={handleReset}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                >
                  <svg
                    className="size-4"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M12 5v14M5 12h14" />
                  </svg>
                  Neue Sitzung starten
                </button>
              </div>
            </div>
            <button
              onClick={() => setPhase("chat")}
              className="self-start text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              {"\u2190"} Zurück zum Gespräch
            </button>
          </div>
          <ReportPreview report={report} />
        </>
      )}
    </>
  );
}
