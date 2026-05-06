"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ReportComparisonData } from "@/types/phonology";

type ProgressSnapshotProps = {
  patientId: string;
};

const CHANGE_STYLES: Record<string, string> = {
  verbessert: "border-green-500/30 bg-green-500/10 text-green-700 dark:text-green-300",
  "unverändert": "border-border bg-surface text-muted-foreground",
  verschlechtert: "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-300",
};

function asComparison(value: unknown): ReportComparisonData | null {
  if (!value || typeof value !== "object") return null;
  const candidate = value as ReportComparisonData;
  return Array.isArray(candidate.items) ? candidate : null;
}

export function ProgressSnapshot({ patientId }: ProgressSnapshotProps) {
  const [comparison, setComparison] = useState<ReportComparisonData | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    setError(null);
    api.patients
      .progress(patientId)
      .then((res) => {
        setComparison(asComparison(res.comparison));
        setMessage(res.message ?? null);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [patientId]);

  return (
    <section className="rounded-lg border border-border bg-card">
      <div className="border-b border-border px-4 py-3">
        <h2 className="text-base font-semibold text-foreground">Fortschritt</h2>
      </div>

      {loading && (
        <div className="px-4 py-8 text-sm text-muted-foreground">
          Lade Fortschritt...
        </div>
      )}

      {error && (
        <div className="px-4 py-4 text-sm text-error-text">{error}</div>
      )}

      {!loading && !error && !comparison && (
        <div className="px-4 py-8 text-sm text-muted-foreground">
          {message ?? "Noch kein Fortschrittsvergleich vorhanden."}
        </div>
      )}

      {!loading && !error && comparison && (
        <div className="grid gap-4 px-4 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
              Gesamtfortschritt
            </p>
            <p className="mt-1 text-sm leading-6 text-foreground">
              {comparison.overall_progress || "-"}
            </p>
          </div>

          {comparison.items.length > 0 && (
            <div className="grid gap-2">
              {comparison.items.slice(0, 4).map((item) => (
                <div
                  key={`${item.category}-${item.change}`}
                  className="grid gap-2 rounded-md border border-border bg-surface/50 px-3 py-2 md:grid-cols-[1fr_auto]"
                >
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium text-foreground">
                      {item.category}
                    </div>
                    <div className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
                      {item.details || item.current_finding}
                    </div>
                  </div>
                  <span
                    className={`inline-flex h-7 items-center rounded-full border px-2.5 text-xs font-medium ${
                      CHANGE_STYLES[item.change] ?? CHANGE_STYLES["unverändert"]
                    }`}
                  >
                    {item.change}
                  </span>
                </div>
              ))}
            </div>
          )}

          {comparison.remaining_issues.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                Offene Punkte
              </p>
              <ul className="mt-2 grid gap-1">
                {comparison.remaining_issues.slice(0, 3).map((issue) => (
                  <li key={issue} className="text-sm text-foreground">
                    {issue}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {comparison.recommendation && (
            <div className="rounded-md border border-accent/20 bg-accent-muted px-3 py-2">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-accent-text">
                Empfehlung
              </p>
              <p className="mt-1 text-sm leading-6 text-foreground">
                {comparison.recommendation}
              </p>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
