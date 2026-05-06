"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { PatientListResponse, PatientSummary } from "@/types";

const PAGE_SIZE = 20;

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function PatientRow({ patient }: { patient: PatientSummary }) {
  return (
    <li>
      <Link
        href={`/patienten/${patient.id}`}
        className="grid gap-3 border-b border-border px-4 py-3 transition-colors hover:bg-surface md:grid-cols-[1.15fr_0.8fr_1fr_8rem]"
      >
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-foreground">
            {patient.pseudonym}
          </div>
          <div className="mt-0.5 text-xs text-muted-foreground">
            {patient.system_id}
          </div>
        </div>
        <div className="text-sm text-muted-foreground">{patient.age_group}</div>
        <div className="min-w-0 truncate text-sm text-muted-foreground">
          {patient.disorder_text || "-"}
        </div>
        <div className="text-sm text-muted-foreground md:text-right">
          {formatDate(patient.created_at)}
        </div>
      </Link>
    </li>
  );
}

export function PatientList() {
  const [query, setQuery] = useState("");
  const [activeQuery, setActiveQuery] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<PatientListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadPatients = useCallback(() => {
    setLoading(true);
    setError(null);
    api.patients
      .list({
        q: activeQuery || undefined,
        page,
        limit: PAGE_SIZE,
      })
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [activeQuery, page]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadPatients();
  }, [loadPatients]);

  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-6 py-8">
      <div className="flex flex-col gap-4 border-b border-border pb-5 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent-text">
            Patientenverwaltung
          </p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">
            Patienten
          </h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/module/report"
            className="inline-flex items-center justify-center rounded-md border border-border bg-surface px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-surface-elevated"
          >
            Berichte
          </Link>
          <Link
            href="/patienten/neu"
            className="inline-flex items-center justify-center rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            Neuer Patient
          </Link>
        </div>
      </div>

      <form
        className="flex flex-col gap-2 sm:flex-row"
        onSubmit={(event) => {
          event.preventDefault();
          setPage(1);
          setActiveQuery(query.trim());
        }}
      >
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Pseudonym oder System-ID"
          className="min-h-10 flex-1 rounded-md border border-border bg-input px-3 text-sm text-foreground outline-none transition-colors placeholder:text-muted focus:border-accent focus:ring-2 focus:ring-ring/20"
        />
        <div className="flex gap-2">
          <button
            type="submit"
            className="min-h-10 rounded-md border border-border bg-surface px-4 text-sm font-medium text-foreground transition-colors hover:bg-surface-elevated"
          >
            Suchen
          </button>
          {(query || activeQuery) && (
            <button
              type="button"
              onClick={() => {
                setQuery("");
                setActiveQuery("");
                setPage(1);
              }}
              className="min-h-10 rounded-md border border-border px-3 text-sm text-muted-foreground transition-colors hover:text-foreground"
              aria-label="Suche zurücksetzen"
            >
              ×
            </button>
          )}
        </div>
      </form>

      {error && (
        <div className="rounded-md border border-error-border bg-error-surface px-4 py-3 text-sm text-error-text">
          {error}
        </div>
      )}

      <section className="overflow-hidden rounded-lg border border-border bg-card">
        <div className="hidden grid-cols-[1.15fr_0.8fr_1fr_8rem] border-b border-border bg-surface px-4 py-2 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground md:grid">
          <span>Patient</span>
          <span>Altersgruppe</span>
          <span>Störungsbild</span>
          <span className="text-right">Angelegt</span>
        </div>

        {loading && (
          <div className="px-4 py-10 text-center text-sm text-muted-foreground">
            Lade Patienten...
          </div>
        )}

        {!loading && !error && data?.items.length === 0 && (
          <div className="flex flex-col items-center gap-3 px-4 py-12 text-center">
            <div className="grid size-10 place-items-center rounded-full bg-accent-muted text-accent-text">
              +
            </div>
            <div>
              <p className="text-sm font-semibold text-foreground">
                Keine Patienten gefunden
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Legen Sie den ersten Datensatz an oder passen Sie die Suche an.
              </p>
            </div>
          </div>
        )}

        {!loading && !error && data && data.items.length > 0 && (
          <ul>
            {data.items.map((patient) => (
              <PatientRow key={patient.id} patient={patient} />
            ))}
          </ul>
        )}
      </section>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage((current) => current - 1)}
            className="rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface disabled:cursor-not-allowed disabled:opacity-40"
          >
            Zurück
          </button>
          <span className="text-sm text-muted-foreground">
            Seite {page} von {totalPages}
          </span>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => setPage((current) => current + 1)}
            className="rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface disabled:cursor-not-allowed disabled:opacity-40"
          >
            Weiter
          </button>
        </div>
      )}
    </div>
  );
}
