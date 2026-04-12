"use client";

import { DictationButton } from "./DictationButton";

const FREE_TEXT_REPORT_TYPES = [
  { key: "befundbericht", label: "Befundbericht" },
  { key: "therapiebericht_kurz", label: "Therapiebericht kurz" },
  { key: "therapiebericht_lang", label: "Therapiebericht lang" },
  { key: "abschlussbericht", label: "Abschlussbericht" },
] as const;

interface FreeTextInputProps {
  reportType: string;
  onReportTypeChange: (type: string) => void;
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  disabled: boolean;
}

export function FreeTextInput({
  reportType,
  onReportTypeChange,
  value,
  onChange,
  onSubmit,
  disabled,
}: FreeTextInputProps) {
  return (
    <div className="flex flex-col gap-3 px-2 pt-2 pb-1">
      <div className="flex flex-wrap gap-2">
        {FREE_TEXT_REPORT_TYPES.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => onReportTypeChange(key)}
            className={[
              "rounded-full border px-4 py-1.5 text-xs font-medium transition-all duration-150",
              reportType === key
                ? "border-accent bg-accent text-white"
                : "border-border-strong text-muted-foreground hover:border-accent/60 hover:text-foreground",
            ].join(" ")}
          >
            {label}
          </button>
        ))}
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        rows={8}
        placeholder="Beschreibe Patient, Diagnose, Therapieverlauf — alles was du weißt. Ich frage nur nach was fehlt."
        className="w-full rounded-lg bg-input border border-border-strong px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-1 focus:ring-accent/50"
        onKeyDown={(e) => {
          if (e.key === "Enter" && e.ctrlKey) {
            e.preventDefault();
            onSubmit();
          }
        }}
      />
      <div className="flex items-center justify-end gap-2">
        <DictationButton
          disabled={disabled}
          onTranscript={(text) => onChange(value ? value + " " + text : text)}
        />
        <button
          onClick={onSubmit}
          disabled={disabled || !value.trim() || !reportType}
          className="rounded-lg bg-accent px-6 py-2 text-sm font-semibold text-white hover:bg-accent/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
        >
          Analysieren {"\u2192"}
        </button>
      </div>
    </div>
  );
}
