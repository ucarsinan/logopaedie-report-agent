"use client";

import { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api } from "@/lib/api";
import { REPORT_TYPE_LABELS } from "@/types";
import type { ReportSummary, ReportDetail, ReportFilterParams, ReportStats } from "@/types";
import { FilterBar } from "./components/FilterBar";
import { StatsCards } from "./components/StatsCards";

const HISTORY_SECTION_LABELS: Record<string, string> = {
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

const HISTORY_SKIP_KEYS = new Set([
  "report_type", "patient", "diagnose", "_db_id", "created_at", "id", "pseudonym",
]);

export function HistoryModule() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<ReportDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [filters, setFilters] = useState<ReportFilterParams>({});
  const [page, setPage] = useState(1);
  const [stats, setStats] = useState<ReportStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);

  const fetchReports = useCallback((params: ReportFilterParams) => {
    setLoading(true);
    setFetchError(null);
    api.reports
      .list(params)
      .then((res) => {
        setReports(res.items);
        setTotal(res.total);
        setPage(res.page);
      })
      .catch((e: Error) => setFetchError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchReports({ ...filters, page });
  }, [filters, page, fetchReports]);

  useEffect(() => {
    api.reports.stats()
      .then(setStats)
      .catch(() => {})
      .finally(() => setStatsLoading(false));
  }, []);

  const handleFilterChange = useCallback((newFilters: ReportFilterParams) => {
    setFilters(newFilters);
    setPage(1);
  }, []);

  const totalPages = Math.ceil(total / (filters.limit ?? 20));

  useEffect(() => {
    if (selectedId === null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDetail(null);
      return;
    }
    setDetailLoading(true);
    api.reports
      .get(selectedId)
      .then(setDetail)
      .catch(() => setDetail(null))
      .finally(() => setDetailLoading(false));
  }, [selectedId]);

  /* Detail view */
  if (selectedId !== null) {
    return (
      <div className="flex flex-col gap-4">
        <button
          onClick={() => setSelectedId(null)}
          className="self-start text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          {"\u2190"} Zurück zur Übersicht
        </button>

        {detailLoading && <p className="text-muted-foreground text-sm">Lade Bericht…</p>}

        {!detailLoading && detail && (
          <>
            <div>
              <h2 className="text-xl font-semibold">
                {REPORT_TYPE_LABELS[detail.report_type] ?? detail.report_type}
              </h2>
              <p className="text-sm text-muted-foreground mt-1">
                {detail.patient?.pseudonym ?? "Unbekannt"} {"\u00b7"}{" "}
                {new Date(detail.created_at).toLocaleDateString("de-DE", {
                  day: "2-digit", month: "2-digit", year: "numeric",
                })}
              </p>
            </div>

            {detail.patient && (
              <section className="p-4 rounded-lg border border-border bg-card">
                <h3 className="font-medium mb-2">Patient</h3>
                <p className="text-sm">Pseudonym: {detail.patient.pseudonym}</p>
                <p className="text-sm">Altersgruppe: {detail.patient.age_group}</p>
                {detail.patient.gender && <p className="text-sm">Geschlecht: {detail.patient.gender}</p>}
              </section>
            )}

            {detail.diagnose && (detail.diagnose.diagnose_text || detail.diagnose.icd_10_codes?.length > 0) && (
              <section className="p-4 rounded-lg border border-border bg-card">
                <h3 className="font-medium mb-2">Diagnose</h3>
                {detail.diagnose.diagnose_text && <p className="text-sm">{detail.diagnose.diagnose_text}</p>}
                {detail.diagnose.indikationsschluessel && (
                  <p className="text-sm text-muted-foreground mt-1">
                    Indikationsschlüssel: {detail.diagnose.indikationsschluessel}
                  </p>
                )}
                {detail.diagnose.icd_10_codes?.length > 0 && (
                  <p className="text-sm text-muted-foreground mt-1">
                    ICD-10: {detail.diagnose.icd_10_codes.join(", ")}
                  </p>
                )}
              </section>
            )}

            {Object.entries(detail)
              .filter(([key, value]) => !HISTORY_SKIP_KEYS.has(key) && value)
              .map(([key, value]) => {
                const label = HISTORY_SECTION_LABELS[key] ?? key;
                if (Array.isArray(value)) {
                  return (
                    <section key={key} className="p-4 rounded-lg border border-border bg-card">
                      <h3 className="font-medium mb-2">{label}</h3>
                      <ul className="list-disc pl-4 space-y-1">
                        {(value as string[]).map((item, i) => (
                          <li key={i} className="text-sm">{item}</li>
                        ))}
                      </ul>
                    </section>
                  );
                }
                return (
                  <section key={key} className="p-4 rounded-lg border border-border bg-card">
                    <h3 className="font-medium mb-2">{label}</h3>
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{String(value)}</ReactMarkdown>
                    </div>
                  </section>
                );
              })}
          </>
        )}
      </div>
    );
  }

  /* List view */
  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-xl font-semibold tracking-tight">Gespeicherte Berichte</h2>

      <StatsCards stats={stats} loading={statsLoading} />
      <FilterBar onFilterChange={handleFilterChange} />

      {loading && <p className="text-muted-foreground text-sm">Lade Berichte…</p>}

      {fetchError && <p className="text-destructive text-sm">Fehler: {fetchError}</p>}

      {!loading && !fetchError && reports.length === 0 && (
        <p className="text-muted-foreground text-sm">
          {total === 0
            ? 'Noch keine Berichte gespeichert. Erstelle deinen ersten Bericht im Tab "Berichterstellung".'
            : "Keine Berichte für diese Filter gefunden."}
        </p>
      )}

      {!loading && !fetchError && reports.length > 0 && (
        <>
          <ul className="space-y-2">
            {reports.map((r) => (
              <li key={r.id}>
                <button
                  onClick={() => setSelectedId(r.id)}
                  className="w-full flex items-center justify-between p-4 rounded-lg border border-border bg-card hover:bg-accent transition-colors text-left"
                >
                  <div>
                    <span className="font-medium">{r.pseudonym}</span>
                    <span className="ml-3 text-sm text-muted-foreground">
                      {REPORT_TYPE_LABELS[r.report_type] ?? r.report_type}
                    </span>
                  </div>
                  <span className="text-sm text-muted-foreground">
                    {new Date(r.created_at).toLocaleDateString("de-DE", {
                      day: "2-digit", month: "2-digit", year: "numeric",
                    })}
                  </span>
                </button>
              </li>
            ))}
          </ul>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-4 pt-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="px-3 py-1.5 text-sm rounded-md border border-border hover:bg-accent transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Zurück
              </button>
              <span className="text-sm text-muted-foreground">
                Seite {page} von {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1.5 text-sm rounded-md border border-border hover:bg-accent transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Weiter
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
