"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ResetConfirmDialog } from "@/components/ResetConfirmDialog";
import { OnboardingOverlay } from "@/components/OnboardingOverlay";
import { ErrorAlert } from "@/components/ErrorAlert";
import { AppShell } from "@/components/AppShell";
import { SessionProvider, useSession } from "@/providers/SessionProvider";
import { PatientContextBar } from "@/features/patients/PatientContextBar";

function ModuleShell({ children }: { children: React.ReactNode }) {
  const searchParams = useSearchParams();
  const patientId = searchParams.get("patient");
  const { isSending, error, handleSoftReset, handleFullReset } = useSession();
  const [isResetDialogOpen, setIsResetDialogOpen] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    const handler = () => setIsResetDialogOpen(true);
    window.addEventListener("request-reset", handler);
    return () => window.removeEventListener("request-reset", handler);
  }, []);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setShowOnboarding(!localStorage.getItem("logopaedie_onboarding_done"));
    }, 0);
    return () => window.clearTimeout(timeoutId);
  }, []);

  const helpButton = (
    <button
      onClick={() => setShowOnboarding(true)}
      className="text-xs text-muted-foreground hover:text-foreground border border-border rounded-full px-2.5 py-0.5 transition-colors"
      title="Einführung anzeigen"
    >
      ? Hilfe
    </button>
  );

  return (
    <AppShell
      headerExtras={helpButton}
      subheader={patientId ? <PatientContextBar patientId={patientId} /> : undefined}
    >
      {error && <ErrorAlert message={error} />}
      {children}

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
    </AppShell>
  );
}

export default function ModuleLayout({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <ModuleShell>{children}</ModuleShell>
    </SessionProvider>
  );
}
