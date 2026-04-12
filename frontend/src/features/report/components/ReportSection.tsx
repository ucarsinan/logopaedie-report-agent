import type { ReactNode } from "react";

interface ReportSectionProps {
  title: string;
  children: ReactNode;
}

export function ReportSection({ title, children }: ReportSectionProps) {
  return (
    <div className="px-6 py-4 bg-surface/60 print:bg-white">
      <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-2 print:text-black print:font-bold print:text-sm print:normal-case">
        {title}
      </h3>
      <div className="text-sm text-foreground leading-relaxed whitespace-pre-wrap print:text-black">
        {children}
      </div>
    </div>
  );
}
