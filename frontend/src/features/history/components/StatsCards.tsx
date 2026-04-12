"use client";

import { REPORT_TYPE_LABELS } from "@/types";
import type { ReportStats } from "@/types";

interface StatsCardsProps {
  stats: ReportStats | null;
  loading: boolean;
}

export function StatsCards({ stats, loading }: StatsCardsProps) {
  if (loading) {
    return <div className="text-sm text-muted-foreground">Lade Statistiken...</div>;
  }
  if (!stats) return null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <div className="p-3 rounded-lg border border-border bg-card text-center">
        <div className="text-2xl font-bold">{stats.total}</div>
        <div className="text-xs text-muted-foreground">Berichte gesamt</div>
      </div>
      {Object.entries(REPORT_TYPE_LABELS).map(([key, label]) => (
        <div key={key} className="p-3 rounded-lg border border-border bg-card text-center">
          <div className="text-2xl font-bold">{stats.by_type[key] ?? 0}</div>
          <div className="text-xs text-muted-foreground">{label}</div>
        </div>
      ))}
      {stats.latest_date && (
        <div className="p-3 rounded-lg border border-border bg-card text-center">
          <div className="text-lg font-bold">
            {new Date(stats.latest_date).toLocaleDateString("de-DE", {
              day: "2-digit", month: "2-digit", year: "numeric",
            })}
          </div>
          <div className="text-xs text-muted-foreground">Letzter Bericht</div>
        </div>
      )}
    </div>
  );
}
