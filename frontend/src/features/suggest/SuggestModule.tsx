"use client";

import { useRef, useState } from "react";
import { api } from "@/lib/api";
import { Spinner } from "@/components/icons";

export function SuggestModule() {
  const [text, setText] = useState("");
  const [reportType, setReportType] = useState("befundbericht");
  const [disorder, setDisorder] = useState("");
  const [section, setSection] = useState("befund");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function onTextChange(val: string) {
    setText(val);
    if (timerRef.current) clearTimeout(timerRef.current);
    if (val.trim().length > 10) {
      timerRef.current = setTimeout(() => fetchSuggestions(val), 800);
    } else {
      setSuggestions([]);
    }
  }

  async function fetchSuggestions(input: string) {
    setLoading(true);
    try {
      const data = await api.suggest(input, reportType, disorder, section);
      setSuggestions(data.suggestions || []);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }

  function applySuggestion(s: string) {
    setText(text + s);
    setSuggestions([]);
  }

  return (
    <>
      {/* Header card */}
      <div
        style={{
          borderLeft: "3px solid var(--border)",
          border: "1px solid var(--border)",
          borderLeftWidth: "3px",
          borderRadius: "0 6px 6px 0",
          padding: "10px 14px",
          background: "var(--surface)",
          marginBottom: "8px",
        }}
      >
        <p style={{ fontSize: "14px", fontWeight: "600", margin: "0 0 3px 0", color: "var(--foreground)" }}>
          {"\u270f\ufe0f"} Textbausteine
        </p>
        <p style={{ fontSize: "12px", color: "var(--muted-foreground)", margin: 0, lineHeight: "1.5" }}>
          Geben Sie einen Text ein — die KI schlägt passende Formulierungen vor. Klicken Sie einen Vorschlag um ihn zu übernehmen.
        </p>
      </div>
      <h1 className="text-xl font-semibold tracking-tight">Intelligente Textbausteine</h1>
      <p className="text-sm text-muted-foreground">
        Beginnen Sie einen Satz und die KI schlägt kontextbezogene Vervollständigungen
        mit logopädischer Fachsprache vor. Klicken Sie auf einen Vorschlag zum Übernehmen.
      </p>

      {/* Context selectors */}
      <div className="flex flex-wrap gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground">Berichtstyp</label>
          <select value={reportType} onChange={(e) => setReportType(e.target.value)}
            className="rounded-lg bg-surface border border-border-strong px-3 py-2 text-sm focus:outline-none focus:border-ring">
            <option value="befundbericht">Befundbericht</option>
            <option value="therapiebericht_kurz">Therapiebericht (kurz)</option>
            <option value="therapiebericht_lang">Therapiebericht (lang)</option>
            <option value="abschlussbericht">Abschlussbericht</option>
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground">Abschnitt</label>
          <select value={section} onChange={(e) => setSection(e.target.value)}
            className="rounded-lg bg-surface border border-border-strong px-3 py-2 text-sm focus:outline-none focus:border-ring">
            <option value="anamnese">Anamnese</option>
            <option value="befund">Befund</option>
            <option value="therapieindikation">Therapieindikation</option>
            <option value="therapieverlauf">Therapieverlauf</option>
            <option value="empfehlung">Empfehlung</option>
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground">Störungsbild</label>
          <input type="text" value={disorder} onChange={(e) => setDisorder(e.target.value)}
            placeholder="z.B. SP1, ST2"
            className="rounded-lg bg-surface border border-border-strong px-3 py-2 text-sm w-32 focus:outline-none focus:border-ring" />
        </div>
      </div>

      {/* Text editor */}
      <div className="relative">
        <textarea
          value={text}
          onChange={(e) => onTextChange(e.target.value)}
          rows={8}
          placeholder="Beginnen Sie hier zu schreiben, z.B. 'Die phonologische Bewertung ergab...'"
          className="w-full rounded-lg bg-surface border border-border-strong px-4 py-3 text-sm leading-relaxed resize-y focus:outline-none focus:border-ring"
        />
        {loading && (
          <div className="absolute top-3 right-3">
            <Spinner />
          </div>
        )}
      </div>

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-widest">
            Vorschläge (klicken zum Übernehmen)
          </h3>
          {suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => applySuggestion(s)}
              className="text-left rounded-lg bg-surface border border-border hover:border-accent px-4 py-3 text-sm text-foreground/80 transition-colors"
            >
              <span className="text-muted">{text}</span>
              <span className="text-accent-text">{s}</span>
            </button>
          ))}
        </div>
      )}
    </>
  );
}
