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
    } catch {
      // Proceed even if consent request fails
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
                  {"\u2190"} Zurück
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
                  href="/module/history"
                  className="text-sm text-muted-foreground hover:underline"
                >
                  Bericht dauerhaft ansehen {"\u2192"}
                </Link>
              )}
              <Link
                href="/module/history"
                className="text-sm text-muted-foreground hover:underline"
              >
                Alle Berichte
              </Link>
            </div>
          </div>
          <ReportPreview report={report} />
        </>
      )}
    </>
  );
}
