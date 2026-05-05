"use client";

import { useState } from "react";

const REPORT_TYPES = [
  { key: "befundbericht", label: "Befundbericht", description: "Erstdiagnostik und Befunderhebung" },
  { key: "therapiebericht_kurz", label: "Therapiebericht kurz", description: "Kompakter Verlaufsbericht" },
  { key: "therapiebericht_lang", label: "Therapiebericht lang", description: "Ausführlicher Therapieverlauf" },
  { key: "abschlussbericht", label: "Abschlussbericht", description: "Therapieende und Ergebnisse" },
] as const;

interface WelcomeScreenProps {
  onSelectReportType: (type: string) => void;
}

export function WelcomeScreen({ onSelectReportType }: WelcomeScreenProps) {
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div className="flex flex-1 flex-col items-center justify-center py-12">
      <div className="w-full max-w-sm">
        <p className="mb-4 text-[11px] font-medium uppercase tracking-widest text-muted-foreground">
          Dokumentationsbeginn
        </p>
        <h1 className="mb-1 text-lg font-semibold text-foreground">
          Berichtstyp auswählen
        </h1>
        <p className="mb-6 text-sm text-muted-foreground">
          Wählen Sie die Dokumentationsform für diese Sitzung.
        </p>

        <div className="divide-y divide-border-strong border border-border-strong">
          {REPORT_TYPES.map(({ key, label, description }) => {
            const isSelected = selected === key;
            return (
              <button
                key={key}
                onClick={() => setSelected(key)}
                className={[
                  "flex w-full items-start gap-3 border-l-[3px] px-4 py-3 text-left transition-colors",
                  isSelected
                    ? "border-l-accent bg-surface-elevated"
                    : "border-l-transparent hover:bg-surface-elevated/50",
                ].join(" ")}
              >
                <div
                  className={[
                    "mt-0.75 size-3.5 shrink-0 rounded-full border",
                    isSelected ? "border-accent bg-accent" : "border-border-strong",
                  ].join(" ")}
                />
                <div>
                  <div className="text-sm font-medium text-foreground">{label}</div>
                  <div className="mt-0.5 text-xs leading-snug text-muted-foreground">{description}</div>
                </div>
              </button>
            );
          })}
        </div>

        <button
          onClick={() => selected && onSelectReportType(selected)}
          disabled={!selected}
          className="mt-4 w-full rounded px-4 py-2.5 text-sm font-medium transition-colors bg-accent text-accent-foreground hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Sitzung starten
        </button>

        <p className="mt-4 text-center text-xs text-muted-foreground">
          Alternativ können Sie den Fall direkt im Eingabefeld beschreiben.
        </p>
      </div>
    </div>
  );
}
