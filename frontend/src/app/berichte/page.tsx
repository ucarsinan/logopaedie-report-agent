"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, ReportSummary, REPORT_TYPE_LABELS } from "@/lib/api";

export default function BerichtePage() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.reports
      .list()
      .then((res) => setReports(res.items))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="min-h-screen bg-background text-foreground p-6 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Bericht-Verlauf</h1>
        <Link
          href="/"
          className="text-sm px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          + Neuer Bericht
        </Link>
      </div>

      {loading && <p className="text-muted-foreground">Lade Berichte…</p>}

      {error && <p className="text-destructive">Fehler: {error}</p>}

      {!loading && !error && reports.length === 0 && (
        <p className="text-muted-foreground">
          Noch keine Berichte gespeichert.{" "}
          <Link href="/" className="underline">
            Ersten Bericht erstellen →
          </Link>
        </p>
      )}

      {!loading && !error && reports.length > 0 && (
        <ul className="space-y-2">
          {reports.map((r) => (
            <li key={r.id}>
              <Link
                href={`/berichte/${r.id}`}
                className="flex items-center justify-between p-4 rounded-lg border border-border bg-card hover:bg-accent transition-colors"
              >
                <div>
                  <span className="font-medium">{r.pseudonym}</span>
                  <span className="ml-3 text-sm text-muted-foreground">
                    {REPORT_TYPE_LABELS[r.report_type] ?? r.report_type}
                  </span>
                </div>
                <span className="text-sm text-muted-foreground">
                  {new Date(r.created_at).toLocaleDateString("de-DE", {
                    day: "2-digit",
                    month: "2-digit",
                    year: "numeric",
                  })}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
