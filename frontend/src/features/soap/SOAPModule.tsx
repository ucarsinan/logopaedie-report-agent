"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { isStaleSessionError } from "@/lib/stale-session";
import { useSession } from "@/providers/SessionProvider";
import { Skeleton, SkeletonSection } from "@/components/Skeleton";
import { REPORT_TYPE_LABELS } from "@/types";
import type { SOAPNote, ReportSummary } from "@/types";

const SOAP_SECTIONS = [
  { key: "subjective" as const, label: "S \u2014 Subjektiv", description: "Angaben des Patienten/der Eltern, Beschwerden, Anamnese" },
  { key: "objective" as const, label: "O \u2014 Objektiv", description: "Befunde, Testergebnisse, Beobachtungen" },
  { key: "assessment" as const, label: "A \u2014 Assessment", description: "Klinische Bewertung, Diagnose, Interpretation" },
  { key: "plan" as const, label: "P \u2014 Plan", description: "Therapieplan, Ziele, n\u00e4chste Schritte" },
];

interface SOAPModuleProps {
  sessionId: string | null;
}

export function SOAPModule({ sessionId }: SOAPModuleProps) {
  const { handleStaleSession } = useSession();
  const [mode, setMode] = useState<"session" | "report">(sessionId ? "session" : "report");
  const [soapNote, setSoapNote] = useState<SOAPNote | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [editData, setEditData] = useState<SOAPNote | null>(null);

  // Report selection state
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [reportsLoading, setReportsLoading] = useState(false);
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);

  useEffect(() => {
    if (mode === "report") {
      setReportsLoading(true);
      api.reports.list()
        .then((res) => setReports(res.items))
        .catch(() => {})
        .finally(() => setReportsLoading(false));
    }
  }, [mode]);

  const generateFromSession = async () => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    setStatus(null);
    try {
      const result = await api.soap.generate(sessionId);
      setSoapNote(result);
      setEditData({ ...result });
      setEditing(true);
      setStatus("SOAP-Notiz generiert. Bitte prüfen und speichern.");
    } catch (e: unknown) {
      if (isStaleSessionError(e)) {
        handleStaleSession();
        return;
      }
      setError(e instanceof Error ? e.message : "SOAP-Generierung fehlgeschlagen");
    } finally {
      setLoading(false);
    }
  };

  const generateFromReport = async () => {
    if (!selectedReportId) return;
    setLoading(true);
    setError(null);
    setStatus(null);
    try {
      const result = await api.soap.fromReport(selectedReportId);
      setSoapNote(result);
      setEditData({ ...result });
      setEditing(true);
      setStatus("SOAP-Notiz generiert. Bitte prüfen und speichern.");
    } catch (e: unknown) {
      if (isStaleSessionError(e)) {
        handleStaleSession();
        return;
      }
      setError(e instanceof Error ? e.message : "SOAP-Generierung fehlgeschlagen");
    } finally {
      setLoading(false);
    }
  };

  const startEditing = () => {
    if (!soapNote) return;
    setEditData({ ...soapNote });
    setEditing(true);
  };

  const cancelEditing = () => {
    setEditing(false);
    setEditData(null);
  };

  const saveEdits = async () => {
    if (!editData) return;
    if (!editData.id) {
      setError("SOAP-Notiz kann ohne ID nicht gespeichert werden.");
      return;
    }

    setSaving(true);
    setError(null);
    setStatus(null);
    try {
      const saved = await api.soap.update(editData.id, editData);
      setSoapNote(saved);
      setEditing(false);
      setEditData(null);
      setStatus("SOAP-Notiz gespeichert.");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "SOAP-Speichern fehlgeschlagen");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-xl font-semibold tracking-tight">SOAP-Notizen</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Generiere strukturierte klinische Notizen im SOAP-Format
        </p>
      </div>

      {/* Mode selection */}
      {!soapNote && !loading && (
        <div className="flex flex-col gap-4">
          <div className="flex gap-2">
            <button
              type="button"
              aria-pressed={mode === "session"}
              onClick={() => setMode("session")}
              className={`px-4 py-2 text-sm rounded-md border transition-colors ${
                mode === "session"
                  ? "border-accent bg-accent text-white"
                  : "border-border hover:bg-accent/50"
              }`}
            >
              Aus aktueller Session
            </button>
            <button
              type="button"
              aria-pressed={mode === "report"}
              onClick={() => setMode("report")}
              className={`px-4 py-2 text-sm rounded-md border transition-colors ${
                mode === "report"
                  ? "border-accent bg-accent text-white"
                  : "border-border hover:bg-accent/50"
              }`}
            >
              Aus gespeichertem Bericht
            </button>
          </div>

          {mode === "session" && (
            <div>
              {sessionId ? (
                <button
                  type="button"
                  onClick={generateFromSession}
                  className="px-4 py-2 text-sm rounded-md bg-accent text-white hover:opacity-90 transition-opacity"
                >
                  SOAP-Notiz generieren
                </button>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Keine aktive Session. Starte zuerst eine Anamnese im Tab &quot;Berichterstellung&quot;.
                </p>
              )}
            </div>
          )}

          {mode === "report" && (
            <div className="flex flex-col gap-3">
              {reportsLoading && <p className="text-sm text-muted-foreground">Lade Berichte…</p>}
              {!reportsLoading && reports.length === 0 && (
                <p className="text-sm text-muted-foreground">Keine gespeicherten Berichte vorhanden.</p>
              )}
              {!reportsLoading && reports.length > 0 && (
                <>
                  <select
                    aria-label="Gespeicherten Bericht für SOAP-Notiz auswählen"
                    value={selectedReportId ?? ""}
                    onChange={(e) => setSelectedReportId(e.target.value ? Number(e.target.value) : null)}
                    className="px-3 py-2 text-sm rounded-md border border-border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
                  >
                    <option value="">Bericht auswählen...</option>
                    {reports.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.pseudonym} — {REPORT_TYPE_LABELS[r.report_type] ?? r.report_type} ({new Date(r.created_at).toLocaleDateString("de-DE")})
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={generateFromReport}
                    disabled={!selectedReportId}
                    className="self-start px-4 py-2 text-sm rounded-md bg-accent text-white hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    SOAP-Notiz generieren
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div
          role="status"
          aria-live="polite"
          aria-label="SOAP-Notiz wird generiert"
          data-testid="soap-generating-skeleton"
          className="flex flex-col gap-4"
        >
          <div className="flex items-center justify-between">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-40" />
          </div>
          {SOAP_SECTIONS.map(({ key }) => (
            <section
              key={key}
              className="flex flex-col gap-2 p-4 rounded-lg border border-border bg-card"
            >
              <Skeleton className="h-4 w-1/4" />
              <Skeleton className="h-3 w-2/3" />
              <div className="mt-2">
                <SkeletonSection
                  headingWidth="w-1/5"
                  lineWidths={["w-full", "w-11/12", "w-3/4"]}
                />
              </div>
            </section>
          ))}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-4 rounded-lg border border-destructive bg-destructive/10 text-destructive text-sm">
          {error}
        </div>
      )}

      {/* Status */}
      {status && (
        <div aria-live="polite" className="p-4 rounded-lg border border-border bg-card text-sm text-muted-foreground">
          {status}
        </div>
      )}

      {/* SOAP Display */}
      {soapNote && !loading && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 className="font-medium">SOAP-Notiz</h3>
            <div className="flex gap-2">
              {!editing && (
                <button
                  type="button"
                  onClick={startEditing}
                  className="px-3 py-1.5 text-sm rounded-md border border-border hover:bg-accent hover:text-white transition-colors"
                >
                  Bearbeiten
                </button>
              )}
              {editing && (
                <>
                  <button
                    type="button"
                    onClick={saveEdits}
                    disabled={saving}
                    className="px-3 py-1.5 text-sm rounded-md bg-accent text-white hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {saving ? "Speichern…" : "Speichern"}
                  </button>
                  <button
                    type="button"
                    onClick={cancelEditing}
                    disabled={saving}
                    className="px-3 py-1.5 text-sm rounded-md border border-border hover:bg-accent hover:text-white transition-colors"
                  >
                    Abbrechen
                  </button>
                </>
              )}
              <button
                type="button"
                onClick={() => { setSoapNote(null); setEditing(false); setEditData(null); setStatus(null); setError(null); }}
                disabled={saving}
                className="px-3 py-1.5 text-sm rounded-md border border-border text-muted-foreground hover:text-foreground transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Neue Notiz
              </button>
            </div>
          </div>

          {SOAP_SECTIONS.map(({ key, label, description }) => (
            <section key={key} className="p-4 rounded-lg border border-border bg-card">
              <h4 className="font-medium text-sm">{label}</h4>
              <p className="text-xs text-muted-foreground mb-2">{description}</p>
              {editing && editData ? (
                <>
                  <label className="sr-only" htmlFor={`soap-${key}`}>
                    {label}
                  </label>
                  <textarea
                    id={`soap-${key}`}
                    value={editData[key]}
                    onChange={(e) =>
                      setEditData((prev) => prev ? { ...prev, [key]: e.target.value } : prev)
                    }
                    rows={4}
                    className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background text-foreground resize-y focus:outline-none focus:ring-1 focus:ring-accent"
                  />
                </>
              ) : (
                <p className="text-sm whitespace-pre-wrap">{soapNote[key]}</p>
              )}
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
