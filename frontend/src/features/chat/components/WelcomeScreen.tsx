"use client";

import { useState } from "react";
import { ChatInput } from "@/features/chat/components/ChatInput";

const REPORT_TYPES = [
  { key: "befundbericht", label: "Befundbericht", description: "Erstdiagnostik und Befunderhebung" },
  { key: "therapiebericht_kurz", label: "Therapiebericht kurz", description: "Kompakter Verlaufsbericht" },
  { key: "therapiebericht_lang", label: "Therapiebericht lang", description: "Ausführlicher Therapieverlauf" },
  { key: "abschlussbericht", label: "Abschlussbericht", description: "Therapieende und Ergebnisse" },
] as const;

type ReportKey = (typeof REPORT_TYPES)[number]["key"];

interface PreviewSection {
  heading: string;
  text: string;
  muted?: boolean;
  faded?: boolean;
}

interface PreviewContent {
  title: string;
  meta: string;
  structure: string;
  sections: PreviewSection[];
}

const PREVIEW_CONTENT: Record<ReportKey, PreviewContent> = {
  befundbericht: {
    title: "Befundbericht",
    meta: "Sitzung: 1 · Bereich: Phonologie",
    structure: "Struktur: Anamnese · Befund · Diagnose · Empfehlung",
    sections: [
      { heading: "Anamnese", text: "Vorstellung zur Abklärung der phonologischen Bewusstheit und Artikulationsentwicklung." },
      { heading: "Befund", text: "Die Silbensegmentierung zeigt sich eingeschränkt; Reimwörter werden sicher erkannt.", muted: true },
      { heading: "Empfehlung", text: "Weiterführende logopädische Diagnostik und Therapieplanung empfohlen.", muted: true, faded: true },
    ],
  },
  therapiebericht_kurz: {
    title: "Therapiebericht kurz",
    meta: "Verlauf: kompakt · Zeitraum: aktuell",
    structure: "Struktur: Verlauf · Ziel · Maßnahme · nächster Schritt",
    sections: [
      { heading: "Verlauf", text: "Die Mitarbeit ist konstant; Übungen zur Lautdifferenzierung werden zunehmend sicher umgesetzt." },
      { heading: "Ziel", text: "Stabilisierung der phonematischen Differenzierung im Anlautbereich.", muted: true },
      { heading: "Nächster Schritt", text: "Fortführung der Übungssequenzen mit alltagsnahen Wortmaterialien.", muted: true, faded: true },
    ],
  },
  therapiebericht_lang: {
    title: "Therapiebericht lang",
    meta: "Verlauf: ausführlich · Bereich: Phonologie",
    structure: "Struktur: Befund · Verlauf · Therapieziel · Empfehlung",
    sections: [
      { heading: "Befund", text: "Die phonologische Bewusstheit zeigt sich im Bereich der Silbensegmentierung eingeschränkt." },
      { heading: "Verlauf", text: "Reimwörter werden korrekt identifiziert; die Lautanalyse im Anlaut ist mit Unterstützung möglich.", muted: true },
      { heading: "Empfehlung", text: "Fortsetzung der logopädischen Therapie mit häuslichen Übungen empfohlen.", muted: true, faded: true },
    ],
  },
  abschlussbericht: {
    title: "Abschlussbericht",
    meta: "Therapieabschluss · Ergebnisdokumentation",
    structure: "Struktur: Ausgangslage · Verlauf · Ergebnis · Empfehlung",
    sections: [
      { heading: "Ausgangslage", text: "Zu Therapiebeginn bestanden Unsicherheiten in der Lautdifferenzierung und Silbensegmentierung." },
      { heading: "Ergebnis", text: "Die Zielübungen wurden überwiegend sicher umgesetzt; Transferleistungen sind im Alltag erkennbar.", muted: true },
      { heading: "Empfehlung", text: "Abschluss der Therapie mit erneuter Vorstellung bei Bedarf.", muted: true, faded: true },
    ],
  },
};

interface WelcomeScreenProps {
  onSelectReportType: (type: string) => void;
  onFreeText: (text: string) => void;
  onError?: (message: string) => void;
  isSending?: boolean;
}

export function WelcomeScreen({ onSelectReportType, onFreeText, onError, isSending }: WelcomeScreenProps) {
  const [selected, setSelected] = useState<string>("befundbericht");

  const preview = PREVIEW_CONTENT[selected as ReportKey];

  return (
    <div className="flex flex-1 flex-col items-center px-6 pt-6 pb-0">
      <div className="w-full max-w-280">

        <div className="mb-6">
          <p className="mb-1 text-[11px] font-medium uppercase tracking-widest text-muted-foreground">
            Dokumentationsbeginn
          </p>
          <h1 className="text-base font-semibold text-foreground">
            Neue Sitzung dokumentieren
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Berichtstyp wählen und mit dem Ausgangsmaterial der Sitzung fortfahren.
          </p>
        </div>

        {/* Single workbench container */}
        <div className="border border-border-strong">

          {/* Top row: report type selector + preview */}
          <div className="grid grid-cols-1 md:grid-cols-[320px_1fr]">

            {/* Left: report type selection + action */}
            <div className="border-b border-border-strong p-6 md:border-b-0 md:border-r">
              <p className="mb-4 text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                Berichtstyp
              </p>

              <div className="divide-y divide-border-strong border border-border-strong">
                {REPORT_TYPES.map(({ key, label, description }) => {
                  const isSelected = selected === key;
                  return (
                    <button
                      key={key}
                      onClick={() => setSelected(key)}
                      className={[
                        "flex w-full items-start gap-3 border-l-[3px] px-4 py-3.5 text-left transition-colors",
                        isSelected
                          ? "border-l-accent bg-surface-elevated"
                          : "border-l-transparent hover:bg-surface-elevated/50",
                      ].join(" ")}
                    >
                      <div
                        className={[
                          "mt-0.5 size-3.5 shrink-0 rounded-full border",
                          isSelected ? "border-accent bg-accent" : "border-border-strong",
                        ].join(" ")}
                      />
                      <div>
                        <div className="text-sm font-medium text-foreground">{label}</div>
                        <div className="mt-0.5 text-xs leading-snug text-muted-foreground">{description}</div>
                      </div>
                    </button>
                  );
                })}
              </div>

              <button
                onClick={() => onSelectReportType(selected)}
                className="mt-5 w-full px-4 py-2.5 text-sm font-medium transition-colors bg-accent text-accent-foreground hover:bg-accent/90"
              >
                Sitzung starten
              </button>
            </div>

            {/* Right: document preview */}
            <div className="p-6">
              <p className="mb-4 text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                Berichtsvorschau
              </p>

              <div className="border border-border-strong bg-surface-elevated px-6 py-6 min-h-75">
                {/* Document header */}
                <div className="mb-5 border-b border-border-strong pb-5">
                  <div className="text-xs font-semibold uppercase tracking-widest text-foreground">
                    {preview.title}
                  </div>
                  <div className="mt-1.5 text-xs tabular-nums text-muted-foreground">
                    {preview.meta}
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {preview.structure}
                  </p>
                </div>

                {preview.sections.map((section, i) => {
                  const isLast = i === preview.sections.length - 1;
                  return isLast ? (
                    <div key={section.heading} className="relative overflow-hidden">
                      <div className="opacity-40">
                        <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                          {section.heading}
                        </p>
                        <p className="text-sm leading-relaxed text-muted-foreground">
                          {section.text}
                        </p>
                      </div>
                      <div className="absolute inset-x-0 bottom-0 h-10 bg-linear-to-t from-surface-elevated to-transparent" />
                    </div>
                  ) : (
                    <div key={section.heading} className="mb-6">
                      <p className={[
                        "mb-2 text-[10px] font-semibold uppercase tracking-widest",
                        section.muted ? "text-muted-foreground" : "text-foreground",
                      ].join(" ")}>
                        {section.heading}
                      </p>
                      <p className={[
                        "text-sm leading-relaxed",
                        section.muted ? "text-muted-foreground" : "text-foreground",
                      ].join(" ")}>
                        {section.text}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>

          </div>

          {/* Bottom row: Ausgangsmaterial + input — inside the same workbench border */}
          <div className="border-t border-border-strong px-6 py-5">
            <p className="mb-1 text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
              Ausgangsmaterial
            </p>
            <p className="mb-3 text-xs text-muted-foreground">
              Beschreiben Sie den Fall direkt oder nutzen Sie die Eingabe als Startpunkt für die Dokumentation.
            </p>
            <ChatInput
              onSend={onFreeText}
              onError={onError}
              disabled={isSending}
              placeholder="Oder beschreiben Sie Ihren Fall frei…"
            />
          </div>

        </div>

      </div>
    </div>
  );
}
