"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ResetConfirmDialog } from "@/components/ResetConfirmDialog";
import { OnboardingOverlay } from "@/components/OnboardingOverlay";
import { ErrorAlert } from "@/components/ErrorAlert";
import { AppShell } from "@/components/AppShell";
import { SessionProvider, useSession } from "@/providers/SessionProvider";
import { PatientContextBar } from "@/features/patients/PatientContextBar";
import { useOnboarding, markOnboardingDone } from "@/hooks/useOnboarding";

function ModuleShell({ children }: { children: React.ReactNode }) {
  const searchParams = useSearchParams();
  const patientId = searchParams.get("patient");
  const { isSending, error, handleSoftReset, handleFullReset } = useSession();
  const { isDone: onboardingDone } = useOnboarding();
  const [isResetDialogOpen, setIsResetDialogOpen] = useState(false);
  const [overlayIntent, setOverlayIntent] = useState<"auto" | "manual" | "hidden">("auto");

  const showOnboarding =
    overlayIntent === "manual" ||
    (overlayIntent === "auto" && !onboardingDone);

  useEffect(() => {
    const handler = () => setIsResetDialogOpen(true);
    window.addEventListener("request-reset", handler);
    return () => window.removeEventListener("request-reset", handler);
  }, []);

  const helpButton = (
    <button
      onClick={() => setOverlayIntent("manual")}
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
            markOnboardingDone();
            setOverlayIntent("hidden");
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
