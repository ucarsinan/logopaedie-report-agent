"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { PhonologicalAnalysisData } from "@/types/phonology";
import { WorkflowStepper } from "@/components/WorkflowStepper";
import type { StepConfig } from "@/components/WorkflowStepper";

const PHONOLOGY_STEPS: StepConfig[] = [
  {
    label: "Eingabe",
    infoTitle: "Wortpaare eingeben",
    infoText: "Geben Sie das Zielwort und die tatsächliche Produktion des Kindes ein. Fügen Sie beliebig viele Paare hinzu.",
  },
  {
    label: "Analyse",
    infoTitle: "Analyse läuft",
    infoText: "Die KI analysiert die phonologischen Prozesse und bewertet den Schweregrad je Wortpaar.",
  },
  {
    label: "Ergebnis",
    infoTitle: "Analyseergebnis",
    infoText: "Prüfen Sie die erkannten Prozesse und Empfehlungen. Klicken Sie auf \u2713 Eingabe um neue Wortpaare zu analysieren.",
    infoVariant: "success" as const,
  },
];

const severityColors: Record<string, string> = {
  leicht: "bg-yellow-900 text-yellow-300",
  mittel: "bg-orange-900 text-orange-300",
  schwer: "bg-red-900 text-red-300",
};

export function PhonologyModule() {
  const [wordPairs, setWordPairs] = useState<{ target: string; production: string }[]>([
    { target: "", production: "" },
  ]);
  const [childAge, setChildAge] = useState("");
  const [result, setResult] = useState<PhonologicalAnalysisData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState(0);

  function addPair() {
    setWordPairs((prev) => [...prev, { target: "", production: "" }]);
  }

  function updatePair(index: number, field: "target" | "production", value: string) {
    setWordPairs((prev) => prev.map((p, i) => (i === index ? { ...p, [field]: value } : p)));
  }

  function removePair(index: number) {
    if (wordPairs.length > 1) setWordPairs((prev) => prev.filter((_, i) => i !== index));
  }

  async function analyze() {
    const valid = wordPairs.filter((p) => p.target.trim() && p.production.trim());
    if (!valid.length) return;
    setLoading(true);
    setStep(1);
    setError(null);
    try {
      const data = await api.analysis.phonologicalText(valid, childAge || undefined);
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
        steps={PHONOLOGY_STEPS}
        currentStep={step}
        onStepClick={step > 0 ? (i) => { setStep(i); if (i === 0) setResult(null); } : undefined}
      />
      <h1 className="text-xl font-semibold tracking-tight">Phonologische Prozessanalyse</h1>
      <p className="text-sm text-muted-foreground">
        Geben Sie Zielwörter und die tatsächliche Produktion des Kindes ein. Die KI identifiziert
        automatisch phonologische Prozesse und bewertet den Schweregrad.
      </p>

      <div className="flex items-center gap-3">
        <label className="text-sm text-muted-foreground">Alter des Kindes:</label>
        <input
          type="text"
          value={childAge}
          onChange={(e) => setChildAge(e.target.value)}
          placeholder="z.B. 4;6 Jahre"
          className="rounded-lg bg-surface border border-border-strong px-3 py-2 text-sm w-40 focus:outline-none focus:border-ring"
        />
      </div>

      <div className="flex flex-col gap-2">
        {wordPairs.map((pair, i) => (
          <div key={i} className="flex items-center gap-2">
            <input
              type="text"
              value={pair.target}
              onChange={(e) => updatePair(i, "target", e.target.value)}
              placeholder="Zielwort"
              className="flex-1 rounded-lg bg-surface border border-border-strong px-3 py-2 text-sm focus:outline-none focus:border-ring"
            />
            <span className="text-muted">{"\u2192"}</span>
            <input
              type="text"
              value={pair.production}
              onChange={(e) => updatePair(i, "production", e.target.value)}
              placeholder="Produktion"
              className="flex-1 rounded-lg bg-surface border border-border-strong px-3 py-2 text-sm focus:outline-none focus:border-ring"
            />
            <button onClick={() => removePair(i)} className="text-muted hover:text-red-400 text-sm px-2">{"\u2715"}</button>
          </div>
        ))}
        <button onClick={addPair} className="self-start text-sm text-accent-text hover:text-accent-text">+ Weiteres Wortpaar</button>
      </div>

      <button
        onClick={analyze}
        disabled={loading}
        className="self-start px-6 py-3 rounded-lg bg-accent hover:bg-accent-hover text-white font-medium text-sm transition-colors disabled:opacity-40"
      >
        {loading ? "Analysiere…" : "Analyse starten"}
      </button>

      {error && <div className="rounded-lg bg-red-950 border border-red-800 px-5 py-4 text-sm text-red-300">{error}</div>}

      {result && (
        <div className="flex flex-col gap-4">
          {/* Results table */}
          <div className="rounded-lg border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-surface text-muted-foreground text-xs uppercase tracking-wider">
                  <th className="px-4 py-3 text-left">Zielwort</th>
                  <th className="px-4 py-3 text-left">Produktion</th>
                  <th className="px-4 py-3 text-left">Prozesse</th>
                  <th className="px-4 py-3 text-left">Schwere</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {result.items.map((item, i) => (
                  <tr key={i} className="bg-surface/60">
                    <td className="px-4 py-3 font-mono">{item.target_word}</td>
                    <td className="px-4 py-3 font-mono text-red-300">{item.production}</td>
                    <td className="px-4 py-3">
                      <ul className="space-y-1">
                        {item.processes.map((p, j) => (
                          <li key={j} className="text-xs text-foreground/80">{p}</li>
                        ))}
                      </ul>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-1 rounded-full ${severityColors[item.severity] || "bg-surface-elevated text-muted-foreground"}`}>
                        {item.severity}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Summary */}
          <div className="rounded-lg border border-border bg-surface/60 px-5 py-4">
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-2">Zusammenfassung</h3>
            <p className="text-sm text-foreground whitespace-pre-wrap">{result.summary}</p>
            <div className="mt-3 flex items-center gap-2">
              <span className={`text-xs px-2 py-1 rounded-full ${result.age_appropriate ? "bg-green-900 text-green-300" : "bg-red-900 text-red-300"}`}>
                {result.age_appropriate ? "Altersgemäß" : "Nicht altersgemäß"}
              </span>
            </div>
            {result.recommended_focus.length > 0 && (
              <div className="mt-3">
                <h4 className="text-xs text-muted-foreground mb-1">Empfohlene Therapieschwerpunkte:</h4>
                <ul className="space-y-1">
                  {result.recommended_focus.map((f, i) => (
                    <li key={i} className="text-sm text-accent-text flex items-start gap-2">
                      <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-accent shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
