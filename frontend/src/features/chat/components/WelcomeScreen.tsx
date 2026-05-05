"use client";

const REPORT_TYPES = [
  {
    key: "befundbericht",
    label: "Befundbericht",
    description: "Erstdiagnostik und Befunderhebung",
    icon: (
      <svg className="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15a2.25 2.25 0 0 1 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z" />
      </svg>
    ),
  },
  {
    key: "therapiebericht_kurz",
    label: "Therapiebericht kurz",
    description: "Kompakter Verlaufsbericht",
    icon: (
      <svg className="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
      </svg>
    ),
  },
  {
    key: "therapiebericht_lang",
    label: "Therapiebericht lang",
    description: "Ausführlicher Therapieverlauf",
    icon: (
      <svg className="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
        <path d="M9 16.5h6M9 12.75h6M9 9h6" />
      </svg>
    ),
  },
  {
    key: "abschlussbericht",
    label: "Abschlussbericht",
    description: "Therapieende und Ergebnisse",
    icon: (
      <svg className="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
      </svg>
    ),
  },
] as const;

interface WelcomeScreenProps {
  onSelectReportType: (type: string) => void;
}

export function WelcomeScreen({ onSelectReportType }: WelcomeScreenProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-8 py-12">
      {/* Header */}
      <div className="text-center">
        <div className="mx-auto mb-4 flex size-14 items-center justify-center rounded-2xl bg-accent/10 text-accent">
          <svg className="size-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 8V4H8" />
            <rect width="16" height="12" x="4" y="8" rx="2" />
            <path d="M2 14h2M20 14h2M15 13v2M9 13v2" />
          </svg>
        </div>
        <h1 className="text-xl font-semibold tracking-tight text-foreground">
          Welchen Bericht möchten Sie erstellen?
        </h1>
        <p className="mt-1.5 text-sm text-muted-foreground">
          Wählen Sie den Berichtstyp — der Assistent führt Sie durch die Anamnese.
        </p>
      </div>

      {/* Report type cards */}
      <div className="grid w-full max-w-lg grid-cols-2 gap-3">
        {REPORT_TYPES.map(({ key, label, description, icon }) => (
          <button
            key={key}
            onClick={() => onSelectReportType(key)}
            className="group flex flex-col gap-2 rounded-xl border border-border-strong bg-surface p-4 text-left transition-all duration-150 hover:border-accent/50 hover:bg-surface-elevated hover:shadow-sm"
          >
            <div className="flex size-9 items-center justify-center rounded-lg bg-accent/10 text-accent transition-colors group-hover:bg-accent/15">
              {icon}
            </div>
            <div>
              <div className="text-sm font-medium text-foreground">{label}</div>
              <div className="mt-0.5 text-xs text-muted-foreground leading-snug">{description}</div>
            </div>
          </button>
        ))}
      </div>

      {/* Hint for free text */}
      <p className="text-xs text-muted-foreground">
        Oder beschreiben Sie Ihren Fall direkt im Eingabefeld unten.
      </p>
    </div>
  );
}
