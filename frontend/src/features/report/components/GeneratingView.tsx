import { Skeleton, SkeletonSection } from "@/components/Skeleton";

export function GeneratingView() {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-label="Bericht wird generiert"
      className="flex flex-col gap-6"
    >
      <div className="flex flex-col items-center gap-1.5 text-center">
        <p className="text-sm font-medium text-foreground">
          KI analysiert die Anamnese…
        </p>
        <p className="text-xs text-muted-foreground">
          Typisch 10–20 Sekunden. Dieses Fenster nicht schließen.
        </p>
      </div>

      <div
        data-testid="report-generating-skeleton"
        className="overflow-hidden rounded-lg border border-border divide-y divide-border"
      >
        <div className="flex items-center justify-between gap-4 bg-surface px-6 py-4">
          <Skeleton className="h-5 w-2/5" />
          <Skeleton className="h-3 w-20" />
        </div>

        <div className="flex flex-col gap-6 bg-card px-6 py-5">
          <SkeletonSection
            headingWidth="w-1/4"
            lineWidths={["w-3/4", "w-2/3"]}
          />
          <SkeletonSection
            headingWidth="w-1/5"
            lineWidths={["w-5/6", "w-3/5"]}
          />
          <SkeletonSection
            headingWidth="w-1/3"
            lineWidths={["w-full", "w-11/12", "w-4/5", "w-3/4"]}
          />
          <SkeletonSection
            headingWidth="w-1/4"
            lineWidths={["w-full", "w-5/6", "w-2/3"]}
          />
        </div>
      </div>
    </div>
  );
}
