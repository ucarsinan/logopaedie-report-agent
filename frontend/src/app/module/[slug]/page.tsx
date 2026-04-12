"use client";

import { use } from "react";
import { notFound } from "next/navigation";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { useSession } from "@/providers/SessionProvider";
import { ReportModule } from "@/features/report/ReportModule";
import { PhonologyModule } from "@/features/phonology/PhonologyModule";
import { TherapyPlanModule } from "@/features/therapy-plan/TherapyPlanModule";
import { CompareModule } from "@/features/compare/CompareModule";
import { SuggestModule } from "@/features/suggest/SuggestModule";
import { HistoryModule } from "@/features/history/HistoryModule";
import { SOAPModule } from "@/features/soap/SOAPModule";

const VALID_SLUGS = new Set([
  "report",
  "phonology",
  "therapy-plan",
  "compare",
  "suggest",
  "history",
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

  switch (slug) {
    case "report":
      return (
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
      );
    case "phonology":
      return <PhonologyModule />;
    case "therapy-plan":
      return <TherapyPlanModule sessionId={session.sessionId} />;
    case "compare":
      return <CompareModule />;
    case "suggest":
      return <SuggestModule />;
    case "history":
      return <HistoryModule />;
    case "soap":
      return <SOAPModule sessionId={session.sessionId} />;
    default:
      notFound();
  }
}
