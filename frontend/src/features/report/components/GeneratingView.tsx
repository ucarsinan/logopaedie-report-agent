export function GeneratingView() {
  return (
    <div
      className="flex flex-col gap-6"
      role="status"
      aria-live="polite"
      aria-label="Bericht wird generiert"
    >
      <div className="flex flex-col items-center gap-1.5 text-center">
        <p className="text-sm font-medium text-foreground">
          KI analysiert die Anamnese…
        </p>
        <p className="text-xs text-muted-foreground">
          Typisch 10–20 Sekunden. Dieses Fenster nicht schließen.
        </p>
      </div>

      <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-5 motion-reduce:[&_*]:animate-none">
        <div className="h-5 w-2/5 animate-pulse rounded bg-muted" />
        <div className="h-3 w-3/4 animate-pulse rounded bg-muted" />
        <div className="h-3 w-5/6 animate-pulse rounded bg-muted" />
        <div className="h-3 w-2/3 animate-pulse rounded bg-muted" />

        <div className="mt-3 h-4 w-1/3 animate-pulse rounded bg-muted" />
        <div className="h-3 w-full animate-pulse rounded bg-muted" />
        <div className="h-3 w-11/12 animate-pulse rounded bg-muted" />

        <div className="mt-3 h-4 w-1/4 animate-pulse rounded bg-muted" />
        <div className="h-3 w-4/5 animate-pulse rounded bg-muted" />
        <div className="h-3 w-3/5 animate-pulse rounded bg-muted" />
      </div>
    </div>
  );
}
