const STEPS = [
  {
    n: "1",
    icon: (
      <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <rect x="3" y="5" width="18" height="14" rx="2" stroke="currentColor" strokeWidth="1.5" />
        <path d="M8 5V3M16 5V3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M3 10h18" stroke="currentColor" strokeWidth="1.5" />
        <path d="M8 14h4M8 17h2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
    title: "Patient & Sitzung",
    description:
      "Patient auswählen oder Demo-Modus starten — keine Registrierung nötig.",
    label: "Setup",
  },
  {
    n: "2",
    icon: (
      <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.5" />
        <path d="M12 4v2M12 18v2M4 12H2M22 12h-2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        <circle cx="12" cy="12" r="1.5" fill="currentColor" />
        <path
          d="M9 3.5C6.5 4.8 4.8 7.2 4.5 10M15 3.5c2.5 1.3 4.2 3.7 4.5 6.5M9 20.5c-2.5-1.3-4.2-3.7-4.5-6.5M15 20.5c2.5-1.3 4.2-3.7 4.5-6.5"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
      </svg>
    ),
    title: "Anamnese führen",
    description:
      "Die KI stellt klinisch relevante Fragen — per Text tippen oder per Sprache antworten.",
    label: "KI-Gespräch",
  },
  {
    n: "3",
    icon: (
      <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M14 3H6a2 2 0 00-2 2v14a2 2 0 002 2h12a2 2 0 002-2V9l-6-6z"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
        <path d="M14 3v6h6" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
        <path d="M8 13h8M8 17h5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
    title: "Bericht generieren",
    description:
      "Llama-3.3-70b erstellt den strukturierten Klinikbericht — als PDF exportierbar.",
    label: "PDF Export",
  },
];

export function HowItWorks() {
  return (
    <section className="w-full max-w-4xl mx-auto px-6 py-14">
      <div className="mb-10 text-center">
        <p className="text-xs font-semibold uppercase tracking-widest text-accent-text mb-2">
          Workflow
        </p>
        <h2 className="text-2xl font-extrabold text-foreground">
          Vom Gespräch zum Bericht in 3 Schritten
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Kein manuelles Tippen. Keine Formatierungsarbeit. Nur Therapie.
        </p>
      </div>

      <div className="relative grid grid-cols-1 gap-6 sm:grid-cols-3">
        {/* Connector line (desktop only) */}
        <div
          aria-hidden="true"
          className="absolute top-11 left-[calc(16.67%+1.5rem)] right-[calc(16.67%+1.5rem)] hidden h-px bg-linear-to-r from-accent/30 via-accent/60 to-accent/30 sm:block"
        />

        {STEPS.map(({ n, icon, title, description, label }) => (
          <div key={n} className="relative flex flex-col gap-4">
            <div className="relative flex h-full flex-col items-center gap-3 rounded-xl border border-border bg-surface p-6 shadow-sm transition-shadow hover:shadow-md">
              {/* Step badge */}
              <span className="absolute -top-3 left-5 flex h-6 w-6 items-center justify-center rounded-full bg-accent text-xs font-bold text-white shadow-sm">
                {n}
              </span>

              {/* Icon container */}
              <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-accent/20 bg-accent-muted text-accent">
                {icon}
              </div>

              {/* Label pill */}
              <span className="rounded-full border border-border bg-background px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
                {label}
              </span>

              <div className="text-center">
                <h3 className="mb-1.5 text-sm font-semibold text-foreground">{title}</h3>
                <p className="text-xs leading-relaxed text-muted-foreground">{description}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
