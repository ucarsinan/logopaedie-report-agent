"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
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
  const [mode, setMode] = useState<"session" | "report">(sessionId ? "session" : "report");
  const [soapNote, setSoapNote] = useState<SOAPNote | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
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
    try {
      const result = await api.soap.generate(sessionId);
      setSoapNote(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "SOAP-Generierung fehlgeschlagen");
    } finally {
      setLoading(false);
    }
  };

  const generateFromReport = async () => {
    if (!selectedReportId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.soap.fromReport(selectedReportId);
      setSoapNote(result);
    } catch (e: unknown) {
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

  const saveEdits = () => {
    if (!editData) return;
    setSoapNote(editData);
    setEditing(false);
    setEditData(null);
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
              onClick={() => setMode("session")}
              className={`px-4 py-2 text-sm rounded-md border transition-colors ${
                mode === "session"
                  ? "border-accent bg-accent text-accent-foreground"
                  : "border-border hover:bg-accent/50"
              }`}
            >
              Aus aktueller Session
            </button>
            <button
              onClick={() => setMode("report")}
              className={`px-4 py-2 text-sm rounded-md border transition-colors ${
                mode === "report"
                  ? "border-accent bg-accent text-accent-foreground"
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
                  onClick={generateFromSession}
                  className="px-4 py-2 text-sm rounded-md bg-accent text-accent-foreground hover:opacity-90 transition-opacity"
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
              {reportsLoading && <p className="text-sm text-muted-foreground">Lade Berichte...</p>}
              {!reportsLoading && reports.length === 0 && (
                <p className="text-sm text-muted-foreground">Keine gespeicherten Berichte vorhanden.</p>
              )}
              {!reportsLoading && reports.length > 0 && (
                <>
                  <select
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
                    onClick={generateFromReport}
                    disabled={!selectedReportId}
                    className="self-start px-4 py-2 text-sm rounded-md bg-accent text-accent-foreground hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
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
        <div className="flex items-center gap-3 p-4 rounded-lg border border-border bg-card">
          <div className="h-5 w-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-muted-foreground">SOAP-Notiz wird generiert...</span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-4 rounded-lg border border-destructive bg-destructive/10 text-destructive text-sm">
          {error}
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
                  onClick={startEditing}
                  className="px-3 py-1.5 text-sm rounded-md border border-border hover:bg-accent transition-colors"
                >
                  Bearbeiten
                </button>
              )}
              {editing && (
                <>
                  <button
                    onClick={saveEdits}
                    className="px-3 py-1.5 text-sm rounded-md bg-accent text-accent-foreground hover:opacity-90"
                  >
                    Speichern
                  </button>
                  <button
                    onClick={cancelEditing}
                    className="px-3 py-1.5 text-sm rounded-md border border-border hover:bg-accent transition-colors"
                  >
                    Abbrechen
                  </button>
                </>
              )}
              <button
                onClick={() => { setSoapNote(null); setEditing(false); setEditData(null); }}
                className="px-3 py-1.5 text-sm rounded-md border border-border text-muted-foreground hover:text-foreground transition-colors"
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
                <textarea
                  value={editData[key]}
                  onChange={(e) =>
                    setEditData((prev) => prev ? { ...prev, [key]: e.target.value } : prev)
                  }
                  rows={4}
                  className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background text-foreground resize-y focus:outline-none focus:ring-1 focus:ring-accent"
                />
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
