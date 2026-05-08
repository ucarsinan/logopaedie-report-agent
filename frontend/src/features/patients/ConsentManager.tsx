"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ConsentRecord, ConsentType } from "@/types";

type ConsentManagerProps = {
  patientId: string;
};

const CONSENT_LABELS: Record<ConsentType, string> = {
  data_processing: "Datenverarbeitung",
  ai_processing: "KI-Verarbeitung",
  data_sharing: "Datenweitergabe",
};

const CONSENT_TYPES = Object.keys(CONSENT_LABELS) as ConsentType[];

function formatDate(value: string): string {
  return new Date(value).toLocaleString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function latestPerType(records: ConsentRecord[]): Partial<Record<ConsentType, ConsentRecord>> {
  const result: Partial<Record<ConsentType, ConsentRecord>> = {};
  for (const r of records) {
    if (!result[r.consent_type]) result[r.consent_type] = r;
  }
  return result;
}

export function ConsentManager({ patientId }: ConsentManagerProps) {
  const [records, setRecords] = useState<Partial<Record<ConsentType, ConsentRecord>>>({});
  const [loading, setLoading] = useState(true);
  const [savingType, setSavingType] = useState<ConsentType | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api.patients
      .consents(patientId)
      .then((list) => setRecords(latestPerType(list)))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [patientId]);

  async function recordConsent(consentType: ConsentType, granted: boolean) {
    setSavingType(consentType);
    setError(null);
    try {
      const record = await api.patients.consent(patientId, consentType, granted);
      setRecords((current) => ({ ...current, [consentType]: record }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Einwilligung konnte nicht gespeichert werden.");
    } finally {
      setSavingType(null);
    }
  }

  return (
    <section className="rounded-lg border border-border bg-card">
      <div className="border-b border-border px-4 py-3">
        <h2 className="text-base font-semibold text-foreground">Einwilligungen</h2>
      </div>

      {error && (
        <div className="border-b border-border px-4 py-3 text-sm text-error-text">
          {error}
        </div>
      )}

      {loading ? (
        <div className="px-4 py-8 text-sm text-muted-foreground">Lade Einwilligungen...</div>
      ) : (
        <ul className="divide-y divide-border">
          {CONSENT_TYPES.map((type) => {
            const record = records[type];
            const isSaving = savingType === type;
            return (
              <li key={type} className="grid gap-3 px-4 py-3 md:grid-cols-[1fr_auto]">
                <div>
                  <div className="text-sm font-medium text-foreground">
                    {CONSENT_LABELS[type]}
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {record
                      ? `${record.granted ? "Erteilt" : "Widerrufen"} · ${formatDate(record.granted_at)}`
                      : "Noch keine Einwilligung erfasst"}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={isSaving}
                    onClick={() => recordConsent(type, true)}
                    className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-surface disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Erteilen
                  </button>
                  <button
                    type="button"
                    disabled={isSaving}
                    onClick={() => recordConsent(type, false)}
                    className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-surface hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Widerrufen
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
