"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { REPORT_TYPE_LABELS, type PatientHistoryItem } from "@/types";

type PatientHistoryProps = {
  patientId: string;
};

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function PatientHistory({ patientId }: PatientHistoryProps) {
  const [items, setItems] = useState<PatientHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    setError(null);
    api.patients
      .history(patientId)
      .then((res) => setItems(res.items))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [patientId]);

  return (
    <section className="rounded-lg border border-border bg-card">
      <div className="border-b border-border px-4 py-3">
        <h2 className="text-base font-semibold text-foreground">Verlauf</h2>
      </div>

      {loading && (
        <div className="px-4 py-8 text-sm text-muted-foreground">
          Lade Verlauf...
        </div>
      )}

      {error && (
        <div className="px-4 py-4 text-sm text-error-text">{error}</div>
      )}

      {!loading && !error && items.length === 0 && (
        <div className="px-4 py-8 text-sm text-muted-foreground">
          Noch keine Berichte vorhanden.
        </div>
      )}

      {!loading && !error && items.length > 0 && (
        <ul>
          {items.map((item) => (
            <li key={`${item.type}-${item.id}`}>
              <Link
                href={`/module/history`}
                className="grid gap-2 border-b border-border px-4 py-3 text-sm transition-colors last:border-b-0 hover:bg-surface md:grid-cols-[1fr_9rem]"
              >
                <div className="min-w-0">
                  <div className="font-medium text-foreground">
                    {REPORT_TYPE_LABELS[item.report_type] ?? item.report_type}
                  </div>
                  <div className="mt-0.5 text-xs text-muted-foreground">
                    {item.pseudonym}
                  </div>
                </div>
                <div className="text-muted-foreground md:text-right">
                  {formatDate(item.created_at)}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
