"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, ReportDetail, REPORT_TYPE_LABELS } from "@/lib/api";

const SECTION_LABELS: Record<string, string> = {
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

const SKIP_KEYS = new Set([
  "report_type", "patient", "diagnose", "_db_id", "created_at",
]);

export default function BerichtDetailPage() {
  const params = useParams();
  const id = Number(params.id);
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.reports
      .get(id)
      .then(setReport)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <main className="min-h-screen bg-background p-6 max-w-3xl mx-auto">
        <p className="text-muted-foreground">Lade Bericht…</p>
      </main>
    );
  }

  if (error || !report) {
    return (
      <main className="min-h-screen bg-background p-6 max-w-3xl mx-auto">
        <p className="text-destructive">{error ?? "Bericht nicht gefunden."}</p>
        <Link href="/berichte" className="underline mt-4 block">
          ← Zurück zur Übersicht
        </Link>
      </main>
    );
  }

  const patient = report.patient;
  const diagnose = report.diagnose;
  const createdAt = new Date(report.created_at).toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });

  return (
    <main className="min-h-screen bg-background text-foreground p-6 max-w-3xl mx-auto">
      <Link href="/berichte" className="text-sm text-muted-foreground hover:underline">
        ← Bericht-Verlauf
      </Link>

      <div className="mt-4 mb-6">
        <h1 className="text-2xl font-semibold">
          {REPORT_TYPE_LABELS[report.report_type] ?? report.report_type}
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          {patient?.pseudonym ?? "Unbekannt"} · {createdAt}
        </p>
      </div>

      {patient && (
        <section className="mb-4 p-4 rounded-lg border border-border bg-card">
          <h2 className="font-medium mb-2">Patient</h2>
          <p className="text-sm">Pseudonym: {patient.pseudonym}</p>
          <p className="text-sm">Altersgruppe: {patient.age_group}</p>
          {patient.gender && <p className="text-sm">Geschlecht: {patient.gender}</p>}
        </section>
      )}

      {diagnose && (diagnose.diagnose_text || diagnose.icd_10_codes?.length > 0) && (
        <section className="mb-4 p-4 rounded-lg border border-border bg-card">
          <h2 className="font-medium mb-2">Diagnose</h2>
          {diagnose.diagnose_text && <p className="text-sm">{diagnose.diagnose_text}</p>}
          {diagnose.indikationsschluessel && (
            <p className="text-sm text-muted-foreground mt-1">
              Indikationsschlüssel: {diagnose.indikationsschluessel}
            </p>
          )}
          {diagnose.icd_10_codes?.length > 0 && (
            <p className="text-sm text-muted-foreground mt-1">
              ICD-10: {diagnose.icd_10_codes.join(", ")}
            </p>
          )}
        </section>
      )}

      {Object.entries(report)
        .filter(([key, value]) => !SKIP_KEYS.has(key) && value)
        .map(([key, value]) => {
          const label = SECTION_LABELS[key] ?? key;
          if (Array.isArray(value)) {
            return (
              <section key={key} className="mb-4 p-4 rounded-lg border border-border bg-card">
                <h2 className="font-medium mb-2">{label}</h2>
                <ul className="list-disc pl-4 space-y-1">
                  {(value as string[]).map((item, i) => (
                    <li key={i} className="text-sm">{item}</li>
                  ))}
                </ul>
              </section>
            );
          }
          return (
            <section key={key} className="mb-4 p-4 rounded-lg border border-border bg-card">
              <h2 className="font-medium mb-2">{label}</h2>
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{String(value)}</ReactMarkdown>
              </div>
            </section>
          );
        })}
    </main>
  );
}
