"use client";

import { useRef, useState } from "react";
import { api } from "@/lib/api";
import type { ReportComparisonData } from "@/types/phonology";
import { WorkflowStepper } from "@/components/WorkflowStepper";
import type { StepConfig } from "@/components/WorkflowStepper";

const COMPARE_STEPS: StepConfig[] = [
  {
    label: "Upload",
    infoTitle: "Berichte hochladen",
    infoText:
      "Laden Sie den Erstbefund und den aktuellen Bericht hoch (PDF, DOCX oder TXT). Die KI analysiert die Unterschiede und erstellt einen strukturierten Fortschrittsbericht.",
  },
  {
    label: "Vergleich",
    infoTitle: "Vergleich läuft",
    infoText: "Die KI analysiert beide Berichte und identifiziert Veränderungen je Bereich.",
  },
  {
    label: "Ergebnis",
    infoTitle: "Vergleichsergebnis",
    infoText:
      "Prüfen Sie die erkannten Veränderungen und die Gesamtempfehlung. Klicken Sie auf \u2713 Upload für einen neuen Vergleich.",
    infoVariant: "success" as const,
  },
];

const changeColors: Record<string, string> = {
  verbessert: "bg-green-900 text-green-300",
  "unverändert": "bg-surface-elevated text-muted-foreground",
  verschlechtert: "bg-red-900 text-red-300",
};

export function CompareModule() {
  const [result, setResult] = useState<ReportComparisonData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const initialRef = useRef<HTMLInputElement>(null);
  const currentRef = useRef<HTMLInputElement>(null);
  const [step, setStep] = useState(0);

  async function compare() {
    const initialFile = initialRef.current?.files?.[0];
    const currentFile = currentRef.current?.files?.[0];
    if (!initialFile || !currentFile) {
      setError("Bitte wählen Sie beide Berichte aus.");
      return;
    }
    setLoading(true);
    setStep(1);
    setError(null);
    try {
      const data = await api.analysis.compare(initialFile, currentFile);
      setResult(data);
      setStep(2);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler.");
      setStep(0);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <WorkflowStepper
        steps={COMPARE_STEPS}
        currentStep={step}
        onStepClick={step > 0 ? (i) => { setStep(i); if (i === 0) setResult(null); } : undefined}
      />
      <h1 className="text-xl font-semibold tracking-tight">Vergleichende Berichtsanalyse</h1>
      <p className="text-sm text-muted-foreground">
        Laden Sie zwei Berichte hoch (z.B. Erstbefund und aktueller Befund). Die KI analysiert
        Veränderungen und erstellt einen strukturierten Fortschrittsbericht.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="flex flex-col gap-2">
          <label className="text-sm text-muted-foreground">Erstbefund / Älterer Bericht:</label>
          <input ref={initialRef} type="file" accept=".pdf,.docx,.txt" className="text-sm text-muted-foreground file:mr-3 file:rounded-lg file:border-0 file:bg-surface-elevated file:px-4 file:py-2 file:text-sm file:text-foreground/80 file:cursor-pointer" />
        </div>
        <div className="flex flex-col gap-2">
          <label className="text-sm text-muted-foreground">Aktueller Bericht:</label>
          <input ref={currentRef} type="file" accept=".pdf,.docx,.txt" className="text-sm text-muted-foreground file:mr-3 file:rounded-lg file:border-0 file:bg-surface-elevated file:px-4 file:py-2 file:text-sm file:text-foreground/80 file:cursor-pointer" />
        </div>
      </div>

      <button
        onClick={compare}
        disabled={loading}
        className="self-start px-6 py-3 rounded-lg bg-accent hover:bg-accent-hover text-white font-medium text-sm transition-colors disabled:opacity-40"
      >
        {loading ? "Vergleiche…" : "Berichte vergleichen"}
      </button>

      {error && <div className="rounded-lg bg-red-950 border border-red-800 px-5 py-4 text-sm text-red-300">{error}</div>}

      {result && (
        <div className="flex flex-col gap-4">
          {/* Comparison table */}
          <div className="rounded-lg border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-surface text-muted-foreground text-xs uppercase tracking-wider">
                  <th className="px-4 py-3 text-left">Bereich</th>
                  <th className="px-4 py-3 text-left">Erstbefund</th>
                  <th className="px-4 py-3 text-left">Aktuell</th>
                  <th className="px-4 py-3 text-left">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {result.items.map((item, i) => (
                  <tr key={i} className="bg-surface/60">
                    <td className="px-4 py-3 font-medium text-foreground/80">{item.category}</td>
                    <td className="px-4 py-3 text-muted-foreground text-xs">{item.initial_finding}</td>
                    <td className="px-4 py-3 text-foreground/80 text-xs">{item.current_finding}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-1 rounded-full ${changeColors[item.change] || "bg-surface-elevated text-muted-foreground"}`}>
                        {item.change}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Summary */}
          <div className="rounded-lg border border-border bg-surface/60 px-5 py-4 space-y-3">
            <div>
              <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-1">Gesamtfortschritt</h3>
              <p className="text-sm text-foreground whitespace-pre-wrap">{result.overall_progress}</p>
            </div>
            {result.remaining_issues.length > 0 && (
              <div>
                <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-1">Verbleibende Probleme</h3>
                <ul className="space-y-1">{result.remaining_issues.map((r, i) => (
                  <li key={i} className="text-sm text-orange-300 flex items-start gap-2">
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-orange-500 shrink-0" />{r}
                  </li>
                ))}</ul>
              </div>
            )}
            <div>
              <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-1">Empfehlung</h3>
              <p className="text-sm text-foreground whitespace-pre-wrap">{result.recommendation}</p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
