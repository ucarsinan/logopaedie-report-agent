const ANAMNESIS_PHASES = [
  { key: "report_type", label: "Berichtstyp" },
  { key: "patient_info", label: "Patient" },
  { key: "disorder", label: "Störungsbild" },
  { key: "anamnesis", label: "Anamnese" },
  { key: "goals", label: "Verlauf" },
  { key: "summary", label: "Abschluss" },
] as const;

type AnamnesisPhaseKey = typeof ANAMNESIS_PHASES[number]["key"];

const PHASE_ORDER: AnamnesisPhaseKey[] = ANAMNESIS_PHASES.map((p) => p.key);

interface AnamnesisProgressProps {
  currentPhase: string;
}

export function AnamnesisProgress({ currentPhase }: AnamnesisProgressProps) {
  const currentIndex = PHASE_ORDER.indexOf(currentPhase as AnamnesisPhaseKey);

  return (
    <div className="flex items-center gap-1 flex-wrap">
      {ANAMNESIS_PHASES.map((phase, i) => {
        const isDone = currentIndex > i;
        const isActive = currentIndex === i;
        return (
          <div key={phase.key} className="flex items-center gap-1">
            {i > 0 && (
              <span className="text-muted text-xs">&rsaquo;</span>
            )}
            <span
              className={`text-xs px-2 py-0.5 rounded-full font-medium transition-colors ${
                isDone
                  ? "line-through opacity-50"
                  : isActive
                  ? "text-white"
                  : "text-muted-foreground"
              }`}
              style={
                isDone
                  ? { background: "var(--accent-muted)", color: "var(--accent-text)" }
                  : isActive
                  ? { background: "var(--accent)" }
                  : { background: "var(--surface-elevated)" }
              }
            >
              {isDone ? `\u2713 ${phase.label}` : phase.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}
