const QUICK_REPLY_TYPES = [
  'Befundbericht',
  'Therapiebericht kurz',
  'Therapiebericht lang',
  'Abschlussbericht',
  '\u270f\ufe0f Sonstiges...',
] as const;

interface QuickReplyBubblesProps {
  onSelect: (type: string) => void;
  disabled: boolean;
}

export function QuickReplyBubbles({ onSelect, disabled }: QuickReplyBubblesProps) {
  return (
    <div className="flex flex-wrap gap-2 pl-10 pt-1">
      {QUICK_REPLY_TYPES.map((t) => {
        const isOther = t.startsWith('\u270f\ufe0f');
        return (
          <button
            key={t}
            onClick={() => onSelect(t)}
            disabled={disabled}
            className={[
              'rounded-full border px-4 py-2 text-sm transition-all duration-150',
              'disabled:opacity-40 disabled:cursor-not-allowed',
              isOther
                ? 'border-border-strong text-muted-foreground hover:text-foreground hover:border-border-strong bg-surface'
                : 'border-accent/50 text-accent-text bg-accent-muted hover:bg-accent-muted/80',
            ].join(' ')}
          >
            {t}
          </button>
        );
      })}
    </div>
  );
}
