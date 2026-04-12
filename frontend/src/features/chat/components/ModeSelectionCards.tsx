interface ModeSelectionCardsProps {
  onSelect: (mode: "free" | "guided") => void;
}

export function ModeSelectionCards({ onSelect }: ModeSelectionCardsProps) {
  return (
    <div className="flex gap-3 pl-2 pt-2 pb-1">
      <button
        onClick={() => onSelect("free")}
        className="flex-1 rounded-xl border border-border-strong bg-surface-2 hover:bg-surface-3 hover:border-accent/60 transition-all duration-150 p-4 text-left"
      >
        <div className="text-base font-semibold text-foreground mb-1">{"\u270f\ufe0f"} Freitext</div>
        <div className="text-xs text-muted-foreground leading-snug">
          Tippe alles auf einmal — ich frage nur nach was fehlt
        </div>
      </button>
      <button
        onClick={() => onSelect("guided")}
        className="flex-1 rounded-xl border border-border-strong bg-surface-2 hover:bg-surface-3 hover:border-accent/60 transition-all duration-150 p-4 text-left"
      >
        <div className="text-base font-semibold text-foreground mb-1">{"\ud83d\udcac"} Geführtes Gespräch</div>
        <div className="text-xs text-muted-foreground leading-snug">
          Schritt für Schritt durch alle relevanten Informationen
        </div>
      </button>
    </div>
  );
}
