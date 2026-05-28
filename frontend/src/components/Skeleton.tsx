interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className = "" }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={`animate-pulse rounded bg-muted motion-reduce:animate-none ${className}`}
    />
  );
}

interface SkeletonSectionProps {
  headingWidth?: string;
  lineWidths?: string[];
}

export function SkeletonSection({
  headingWidth = "w-1/3",
  lineWidths = ["w-full", "w-11/12", "w-4/5"],
}: SkeletonSectionProps) {
  return (
    <div className="flex flex-col gap-3">
      <Skeleton className={`h-4 ${headingWidth}`} />
      {lineWidths.map((w, i) => (
        <Skeleton key={i} className={`h-3 ${w}`} />
      ))}
    </div>
  );
}
