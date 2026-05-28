"use client";

import { use, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { notFound } from "next/navigation";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { useSession } from "@/providers/SessionProvider";
import { useDemoMode } from "@/hooks/useDemoMode";
import { PatientPickerModal } from "@/features/patients/PatientPickerModal";
import { ReportModule } from "@/features/report/ReportModule";
import { PhonologyModule } from "@/features/phonology/PhonologyModule";
import { TherapyPlanModule } from "@/features/therapy-plan/TherapyPlanModule";
import { CompareModule } from "@/features/compare/CompareModule";
import { SuggestModule } from "@/features/suggest/SuggestModule";
import { HistoryModule } from "@/features/history/HistoryModule";
import { SOAPModule } from "@/features/soap/SOAPModule";
import type { PatientSummary } from "@/types";

const VALID_SLUGS = new Set([
  "report",
  "phonology",
  "therapy-plan",
  "compare",
  "suggest",
  "history",
  "soap",
]);

/** Slugs that require a patient context before starting */
const PATIENT_REQUIRED_SLUGS = new Set([
  "report",
  "phonology",
  "therapy-plan",
  "soap",
]);

const FALLBACK_TITLES: Record<string, string> = {
  report: "Berichterstellung-Fehler",
  phonology: "Phonologie-Fehler",
  "therapy-plan": "Therapieplan-Fehler",
  compare: "Vergleich-Fehler",
  suggest: "Textbausteine-Fehler",
  history: "Verlauf-Fehler",
  soap: "SOAP-Fehler",
};

export default function ModulePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = use(params);

  if (!VALID_SLUGS.has(slug)) {
    notFound();
  }

  return (
    <ErrorBoundary fallbackTitle={FALLBACK_TITLES[slug]}>
      <ModuleContent slug={slug} />
    </ErrorBoundary>
  );
}

function ModuleContent({ slug }: { slug: string }) {
  const session = useSession();
  const router = useRouter();
  const searchParams = useSearchParams();

  const patientId = searchParams.get("patient");
  const { isDemo } = useDemoMode();
  const [dismissedSlug, setDismissedSlug] = useState<string | null>(null);

  const dismissed = dismissedSlug === slug;

  const showPicker =
    PATIENT_REQUIRED_SLUGS.has(slug) && !patientId && !isDemo && !dismissed;

  function handlePatientSelect(patient: PatientSummary) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("patient", patient.id);
    router.replace(`?${params.toString()}`);
  }

  function handleDismiss() {
    setDismissedSlug(slug);
  }

  return (
    <>
      <PatientPickerModal
        open={showPicker}
        onSelect={handlePatientSelect}
        onDismiss={handleDismiss}
      />

      {slug === "report" && (
        <ReportModule
          sessionId={session.sessionId}
          setSessionId={session.setSessionId}
          messages={session.messages}
          setMessages={session.setMessages}
          error={session.error}
          setError={session.setError}
          isSending={session.isSending}
          setIsSending={session.setIsSending}
          onRequestReset={() => {
            /* Reset dialog is in the layout */
            const event = new CustomEvent("request-reset");
            window.dispatchEvent(event);
          }}
        />
      )}
      {slug === "phonology" && <PhonologyModule />}
      {slug === "therapy-plan" && <TherapyPlanModule />}
      {slug === "compare" && <CompareModule />}
      {slug === "suggest" && <SuggestModule />}
      {slug === "history" && <HistoryModule />}
      {slug === "soap" && <SOAPModule sessionId={session.sessionId} />}
    </>
  );
}
