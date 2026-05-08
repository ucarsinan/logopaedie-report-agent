"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { REPORT_TYPE_LABELS } from "@/types";
import type { ReportSummary } from "@/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "/backend-api";

async function fetchRecentReports(): Promise<ReportSummary[]> {
  try {
    const res = await fetch(`${API}/reports?limit=5`, {
      credentials: "include",
    });
    // Not authenticated or any other error → render nothing
    if (!res.ok) return [];
    const data = await res.json();
    return data.items ?? [];
  } catch {
    return [];
  }
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function AvatarInitial({ name }: { name: string }) {
  const initial = name.trim().charAt(0).toUpperCase();
  return (
    <span
      aria-hidden="true"
      className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent text-xs font-semibold text-white"
    >
      {initial}
    </span>
  );
}

function DemoBadge() {
  return (
    <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
      Demo
    </span>
  );
}

function ReportCard({ report }: { report: ReportSummary }) {
  const label = REPORT_TYPE_LABELS[report.report_type] ?? report.report_type;
  const date = formatDate(report.created_at);

  if (report.patient_id && report.patient_pseudonym) {
    return (
      <Link
        href={`/patienten/${report.patient_id}`}
        className="flex items-center gap-3 rounded-lg border border-border bg-card px-4 py-3 transition-colors hover:bg-surface"
      >
        <AvatarInitial name={report.patient_pseudonym} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-foreground">
            {report.patient_pseudonym}
          </p>
          <p className="truncate text-xs text-muted-foreground">{label}</p>
        </div>
        <p className="shrink-0 text-xs text-muted-foreground">{date}</p>
      </Link>
    );
  }

  return (
    <Link
      href={`/module/history?report=${report.id}`}
      className="flex items-center gap-3 rounded-lg border border-border bg-card px-4 py-3 transition-colors hover:bg-surface"
    >
      <DemoBadge />
      <div className="min-w-0 flex-1">
        <p className="truncate text-xs text-muted-foreground">{label}</p>
      </div>
      <p className="shrink-0 text-xs text-muted-foreground">{date}</p>
    </Link>
  );
}

export function RecentReportsSection() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    fetchRecentReports()
      .then(setReports)
      .finally(() => setLoaded(true));
  }, []);

  // Hide section entirely until loaded and only if there are reports
  if (!loaded || reports.length === 0) return null;

  return (
    <section className="max-w-5xl mx-auto px-6 py-8">
      <h2 className="text-lg font-semibold text-foreground mb-4">
        Zuletzt bearbeitet
      </h2>
      <div className="flex flex-col gap-2">
        {reports.map((report) => (
          <ReportCard key={report.id} report={report} />
        ))}
      </div>
    </section>
  );
}
