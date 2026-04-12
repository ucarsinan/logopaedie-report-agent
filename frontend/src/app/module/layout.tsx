"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ResetConfirmDialog } from "@/components/ResetConfirmDialog";
import { OnboardingOverlay } from "@/components/OnboardingOverlay";
import { ErrorAlert } from "@/components/ErrorAlert";
import { SessionProvider, useSession } from "@/providers/SessionProvider";

const MODULE_TABS: [string, string, string][] = [
  ["report", "Berichterstellung", "KI-geführtes Anamnesegespräch → professioneller Bericht"],
  ["phonology", "Ausspracheanalyse", "Phonologische Prozesse aus Wortpaaren automatisch erkennen"],
  ["therapy-plan", "Therapieplan", "ICF-basierten Therapieplan automatisch generieren"],
  ["compare", "Berichtsvergleich", "Zwei Berichte gegenüberstellen und Fortschritt messen"],
  ["suggest", "Textbausteine", "KI-Formulierungsvorschläge während des Schreibens"],
  ["history", "Bericht-Verlauf", "Alle gespeicherten Berichte anzeigen und durchsuchen"],
  ["soap", "SOAP-Notizen", "Strukturierte klinische Notizen im SOAP-Format generieren"],
];

const MODULE_LABELS: Record<string, string> = Object.fromEntries(
  MODULE_TABS.map(([key, label]) => [key, label]),
);

function ModuleShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const activeSlug = pathname.split("/").pop() ?? "report";
  const { isSending, error, handleSoftReset, handleFullReset } = useSession();
  const [isResetDialogOpen, setIsResetDialogOpen] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(() => {
    if (typeof window === "undefined") return false;
    return !localStorage.getItem("logopaedie_onboarding_done");
  });

  useEffect(() => {
    const handler = () => setIsResetDialogOpen(true);
    window.addEventListener("request-reset", handler);
    return () => window.removeEventListener("request-reset", handler);
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
                {MODULE_LABELS[activeSlug] ?? "Modul"}
              </span>
            </div>
            <div className="flex items-center gap-3">
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

          <nav className="relative flex gap-1 -mb-px overflow-x-auto after:pointer-events-none after:absolute after:right-0 after:top-0 after:h-full after:w-8 after:bg-gradient-to-l after:from-background after:to-transparent md:after:hidden">
            {MODULE_TABS.map(([key, label, tooltip]) => (
              <Link
                key={key}
                href={`/module/${key}`}
                title={tooltip}
                className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  activeSlug === key
                    ? "border-[var(--accent)] text-[var(--accent-text)]"
                    : "border-transparent text-muted-foreground hover:text-foreground hover:border-border-strong"
                }`}
              >
                {label}
              </Link>
            ))}
          </nav>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-8 flex flex-col gap-6">
        {error && <ErrorAlert message={error} />}
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-border px-6 py-4 text-center text-xs text-muted print:hidden">
        Logopädie Report Agent · Groq API · FastAPI + Next.js
      </footer>

      <ResetConfirmDialog
        isOpen={isResetDialogOpen}
        onClose={() => setIsResetDialogOpen(false)}
        onSoftReset={async () => { await handleSoftReset(); setIsResetDialogOpen(false); }}
        onFullReset={async () => { await handleFullReset(); setIsResetDialogOpen(false); }}
        isSending={isSending}
      />

      {showOnboarding && (
        <OnboardingOverlay
          onComplete={() => {
            localStorage.setItem("logopaedie_onboarding_done", "true");
            setShowOnboarding(false);
          }}
        />
      )}
    </div>
  );
}

export default function ModuleLayout({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <ModuleShell>{children}</ModuleShell>
    </SessionProvider>
  );
}
