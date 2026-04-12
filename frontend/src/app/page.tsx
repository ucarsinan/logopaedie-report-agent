"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ResetConfirmDialog } from "@/components/ResetConfirmDialog";
import { OnboardingOverlay } from "@/components/OnboardingOverlay";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { ErrorAlert } from "@/components/ErrorAlert";
import { api } from "@/lib/api";
import type { AppModule, ChatMsg } from "@/types";
import { ReportModule } from "@/features/report/ReportModule";
import { PhonologyModule } from "@/features/phonology/PhonologyModule";
import { TherapyPlanModule } from "@/features/therapy-plan/TherapyPlanModule";
import { CompareModule } from "@/features/compare/CompareModule";
import { SuggestModule } from "@/features/suggest/SuggestModule";
import { HistoryModule } from "@/features/history/HistoryModule";

const SESSION_STORAGE_KEY = "logopaedie_session_id";

const MODULE_LABELS: Record<AppModule, string> = {
  report: "Berichterstellung",
  phonology: "Ausspracheanalyse",
  "therapy-plan": "Therapieplan",
  compare: "Berichtsvergleich",
  suggest: "Textbausteine",
  history: "Bericht-Verlauf",
};

const MODULE_TABS: [AppModule, string, string][] = [
  ["report", "Berichterstellung", "KI-geführtes Anamnesegespräch \u2192 professioneller Bericht"],
  ["phonology", "Ausspracheanalyse", "Phonologische Prozesse aus Wortpaaren automatisch erkennen"],
  ["therapy-plan", "Therapieplan", "ICF-basierten Therapieplan automatisch generieren"],
  ["compare", "Berichtsvergleich", "Zwei Berichte gegenüberstellen und Fortschritt messen"],
  ["suggest", "Textbausteine", "KI-Formulierungsvorschläge während des Schreibens"],
  ["history", "Bericht-Verlauf", "Alle gespeicherten Berichte anzeigen und durchsuchen"],
];

export default function Home() {
  const [activeModule, setActiveModule] = useState<AppModule>("report");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isResetDialogOpen, setIsResetDialogOpen] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);

  // Read module from URL on mount
  useEffect(() => {
    const m = new URLSearchParams(window.location.search).get("module");
    const valid: AppModule[] = ["report", "phonology", "therapy-plan", "compare", "suggest"];
    if (valid.includes(m as AppModule)) {
      setActiveModule(m as AppModule);
    }
    // Onboarding on first visit
    if (typeof window !== "undefined" && !localStorage.getItem("logopaedie_onboarding_done")) {
      setShowOnboarding(true);
    }
  }, []);

  const handleModuleChange = (module: AppModule) => {
    setActiveModule(module);
    const url = new URL(window.location.href);
    url.searchParams.set("module", module);
    window.history.replaceState({}, "", url.toString());
  };

  // Reset handlers
  const handleSoftReset = useCallback(async () => {
    if (!sessionId) return;
    setIsSending(true);
    setError(null);
    try {
      const data = await api.sessions.newConversation(sessionId);
      setMessages(
        data.collected_data?.greeting
          ? [{ role: "assistant", content: data.collected_data.greeting }]
          : []
      );
      const resetFn = (window as unknown as Record<string, unknown>).__reportModuleReset;
      if (typeof resetFn === "function") (resetFn as () => void)();
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
      const data = await api.sessions.create();
      setSessionId(data.session_id);
      localStorage.setItem(SESSION_STORAGE_KEY, data.session_id);
      setMessages(
        data.collected_data?.greeting
          ? [{ role: "assistant", content: data.collected_data.greeting }]
          : []
      );
      const resetFn = (window as unknown as Record<string, unknown>).__reportModuleReset;
      if (typeof resetFn === "function") (resetFn as () => void)();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unbekannter Fehler.");
    } finally {
      setIsSending(false);
      setIsResetDialogOpen(false);
    }
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Header */}
      <header className="border-b border-border print:hidden">
        <div className="max-w-5xl mx-auto px-6">
          <div className="flex items-center justify-between h-12">
            <div className="flex items-center gap-2 text-sm">
              <span className="font-extrabold tracking-tight text-foreground">Logopädie</span>
              <span className="text-border-strong font-light">/</span>
              <span className="font-semibold" style={{ color: "var(--accent-text)" }}>
                {MODULE_LABELS[activeModule]}
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
                onClick={() => setShowOnboarding(true)}
                className="text-xs text-muted-foreground hover:text-foreground border border-border rounded-full px-2.5 py-0.5 transition-colors"
                title="Einführung anzeigen"
              >
                ? Hilfe
              </button>
              <ThemeToggle />
            </div>
          </div>

          <nav className="flex gap-1 -mb-px overflow-x-auto">
            {MODULE_TABS.map(([key, label, tooltip]) => (
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
        {error && <ErrorAlert message={error} />}

        <ErrorBoundary fallbackTitle="Modul-Fehler">
          {activeModule === "report" && (
            <ReportModule
              sessionId={sessionId}
              setSessionId={setSessionId}
              messages={messages}
              setMessages={setMessages}
              error={error}
              setError={setError}
              isSending={isSending}
              setIsSending={setIsSending}
              onRequestReset={() => setIsResetDialogOpen(true)}
            />
          )}
        </ErrorBoundary>

        <ErrorBoundary fallbackTitle="Phonologie-Fehler">
          {activeModule === "phonology" && <PhonologyModule />}
        </ErrorBoundary>

        <ErrorBoundary fallbackTitle="Therapieplan-Fehler">
          {activeModule === "therapy-plan" && <TherapyPlanModule sessionId={sessionId} />}
        </ErrorBoundary>

        <ErrorBoundary fallbackTitle="Vergleich-Fehler">
          {activeModule === "compare" && <CompareModule />}
        </ErrorBoundary>

        <ErrorBoundary fallbackTitle="Textbausteine-Fehler">
          {activeModule === "suggest" && <SuggestModule />}
        </ErrorBoundary>

        <ErrorBoundary fallbackTitle="Verlauf-Fehler">
          {activeModule === "history" && <HistoryModule />}
        </ErrorBoundary>
      </main>

      {/* Footer */}
      <footer className="border-t border-border px-6 py-4 text-center text-xs text-muted print:hidden">
        Logopädie Report Agent {"\u00b7"} Groq API {"\u00b7"} FastAPI + Next.js
      </footer>

      <ResetConfirmDialog
        isOpen={isResetDialogOpen}
        onClose={() => setIsResetDialogOpen(false)}
        onSoftReset={handleSoftReset}
        onFullReset={handleFullReset}
        isSending={isSending}
      />

      {showOnboarding && (
        <OnboardingOverlay onComplete={() => {
          localStorage.setItem("logopaedie_onboarding_done", "true");
          setShowOnboarding(false);
        }} />
      )}
    </div>
  );
}
