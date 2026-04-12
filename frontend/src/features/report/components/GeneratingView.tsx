import { Spinner } from "@/components/icons";

export function GeneratingView() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-4">
      <Spinner />
      <p className="text-sm text-muted-foreground">
        Bericht wird generiert… Dies kann einen Moment dauern.
      </p>
    </div>
  );
}
