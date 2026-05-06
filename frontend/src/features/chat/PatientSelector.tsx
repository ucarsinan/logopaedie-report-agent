"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { PatientSummary } from "@/types";

type PatientSelectorProps = {
  onSelect: (patient: PatientSummary) => void;
  onDemo: () => void;
  loading?: boolean;
};

export function PatientSelector({ onSelect, onDemo, loading }: PatientSelectorProps) {
  const [query, setQuery] = useState("");
  const [activeQuery, setActiveQuery] = useState("");
  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadPatients = useCallback(() => {
    setListLoading(true);
    setError(null);
    api.patients
      .list({ q: activeQuery || undefined, limit: 8 })
      .then((res) => setPatients(res.items))
      .catch((e: Error) => setError(e.message))
      .finally(() => setListLoading(false));
  }, [activeQuery]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadPatients();
  }, [loadPatients]);

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-5">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent-text">
          Sitzungsstart
        </p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">
          Patient auswählen
        </h1>
      </div>

      <section className="rounded-lg border border-border bg-card">
        <form
          className="flex flex-col gap-2 border-b border-border p-4 sm:flex-row"
          onSubmit={(event) => {
            event.preventDefault();
            setActiveQuery(query.trim());
          }}
        >
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Pseudonym oder System-ID"
            className="min-h-10 flex-1 rounded-md border border-border bg-input px-3 text-sm text-foreground outline-none transition-colors placeholder:text-muted focus:border-accent focus:ring-2 focus:ring-ring/20"
          />
          <button
            type="submit"
            className="min-h-10 rounded-md border border-border bg-surface px-4 text-sm font-medium text-foreground transition-colors hover:bg-surface-elevated"
          >
            Suchen
          </button>
        </form>

        {error && (
          <div className="border-b border-border px-4 py-3 text-sm text-error-text">
            {error}
          </div>
        )}

        {listLoading && (
          <div className="px-4 py-8 text-sm text-muted-foreground">
            Lade Patienten...
          </div>
        )}

        {!listLoading && !error && patients.length === 0 && (
          <div className="px-4 py-8 text-sm text-muted-foreground">
            Keine Patienten gefunden.
          </div>
        )}

        {!listLoading && !error && patients.length > 0 && (
          <ul className="divide-y divide-border">
            {patients.map((patient) => (
              <li key={patient.id}>
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => onSelect(patient)}
                  className="grid w-full gap-1 px-4 py-3 text-left transition-colors hover:bg-surface disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <span className="text-sm font-semibold text-foreground">
                    {patient.pseudonym}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {patient.system_id} · {patient.age_group}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-between">
        <button
          type="button"
          disabled={loading}
          onClick={onDemo}
          className="inline-flex min-h-10 items-center justify-center rounded-md border border-border px-4 text-sm font-medium text-muted-foreground transition-colors hover:bg-surface hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50"
        >
          Demo-Modus
        </button>
        <Link
          href="/patienten/neu"
          className="inline-flex min-h-10 items-center justify-center rounded-md bg-accent px-4 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
        >
          Neuer Patient
        </Link>
      </div>
    </div>
  );
}
