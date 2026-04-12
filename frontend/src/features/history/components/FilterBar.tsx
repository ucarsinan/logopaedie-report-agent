"use client";

import { useEffect, useRef, useState } from "react";
import { REPORT_TYPE_LABELS } from "@/types";
import type { ReportFilterParams } from "@/types";

interface FilterBarProps {
  onFilterChange: (filters: ReportFilterParams) => void;
}

export function FilterBar({ onFilterChange }: FilterBarProps) {
  const [pseudonym, setPseudonym] = useState("");
  const [reportType, setReportType] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      onFilterChange({
        pseudonym: pseudonym || undefined,
        report_type: reportType || undefined,
        from_date: fromDate || undefined,
        to_date: toDate || undefined,
        page: 1,
      });
    }, 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [pseudonym, reportType, fromDate, toDate, onFilterChange]);

  const handleReset = () => {
    setPseudonym("");
    setReportType("");
    setFromDate("");
    setToDate("");
  };

  return (
    <div className="flex flex-wrap gap-3 items-end p-4 rounded-lg border border-border bg-card">
      <div className="flex flex-col gap-1 w-full sm:min-w-[160px] sm:w-auto sm:flex-1">
        <label className="text-xs text-muted-foreground">Pseudonym</label>
        <input
          type="text"
          value={pseudonym}
          onChange={(e) => setPseudonym(e.target.value)}
          placeholder="Suche..."
          className="px-3 py-1.5 text-sm rounded-md border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-accent"
        />
      </div>
      <div className="flex flex-col gap-1 w-full sm:min-w-[160px] sm:w-auto">
        <label className="text-xs text-muted-foreground">Berichttyp</label>
        <select
          value={reportType}
          onChange={(e) => setReportType(e.target.value)}
          className="px-3 py-1.5 text-sm rounded-md border border-border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
        >
          <option value="">Alle</option>
          {Object.entries(REPORT_TYPE_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-xs text-muted-foreground">Von</label>
        <input
          type="date"
          value={fromDate}
          onChange={(e) => setFromDate(e.target.value)}
          className="px-3 py-1.5 text-sm rounded-md border border-border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
        />
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-xs text-muted-foreground">Bis</label>
        <input
          type="date"
          value={toDate}
          onChange={(e) => setToDate(e.target.value)}
          className="px-3 py-1.5 text-sm rounded-md border border-border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
        />
      </div>
      <button
        onClick={handleReset}
        className="px-3 py-1.5 text-sm rounded-md border border-border text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
      >
        Zurücksetzen
      </button>
    </div>
  );
}
