const CLINICAL_FEATURES = [
  {
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M12 1a4 4 0 014 4v6a4 4 0 01-8 0V5a4 4 0 014-4z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
        <path d="M8 13a4 4 0 008 0M12 17v4M9 21h6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
    title: "Sprachaufnahme → Bericht",
    description:
      "Groq Whisper transkribiert die Therapiesitzung in Echtzeit. Llama-3.3-70b strukturiert daraus einen professionellen Befundbericht.",
  },
  {
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2" stroke="currentColor" strokeWidth="1.5" />
        <rect x="9" y="3" width="6" height="4" rx="1" stroke="currentColor" strokeWidth="1.5" />
        <path d="M9 12h6M9 16h4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
    title: "SOAP-Notes automatisch",
    description:
      "Strukturierte klinische Dokumentation im S-O-A-P-Format — in Sekunden generiert, sofort exportierbar.",
  },
  {
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M3 17l4-8 4 5 3-3 4 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M3 21h18" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
    title: "Phonologische Analyse",
    description:
      "Störungsmuster wie Plosivierung oder Fronting werden automatisch aus Wortpaaren erkannt und dokumentiert.",
  },
  {
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="1.5" />
        <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
    title: "Patientenverwaltung",
    description:
      "Persistente Patientenprofile mit verschlüsselten Stammdaten und sitzungsübergreifendem Therapieverlauf.",
  },
];

const TECH_FEATURES = [
  {
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <rect x="2" y="3" width="20" height="14" rx="2" stroke="currentColor" strokeWidth="1.5" />
        <path d="M8 21h8M12 17v4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M7 8l3 3-3 3M13 14h4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    title: "Multi-user Auth",
    description:
      "Registrierung, E-Mail-Verifikation, TOTP 2FA, Passwort-Reset und aktive Sessions mit Geräte-Revoke.",
  },
  {
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M14 3H6a2 2 0 00-2 2v14a2 2 0 002 2h12a2 2 0 002-2V9l-6-6z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
        <path d="M14 3v6h6" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
        <path d="M9 15l1.5 1.5L13 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    title: "PDF Export",
    description:
      "Professionelle PDFs via ReportLab — mit Patientendaten, Diagnose, Abschnittsgliederung und Unterschriftsfeld.",
  },
  {
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <rect x="3" y="11" width="18" height="10" rx="2" stroke="currentColor" strokeWidth="1.5" />
        <path d="M7 11V7a5 5 0 0110 0v4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        <circle cx="12" cy="16" r="1.5" fill="currentColor" />
      </svg>
    ),
    title: "Fernet-verschlüsselt",
    description:
      "Session-Daten in Upstash Redis Fernet-verschlüsselt, Reports persistent in Neon PostgreSQL via SQLModel.",
  },
  {
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    title: "API-first Backend",
    description:
      "9 FastAPI-Router, 35 pytest-Tests, Rate Limiting via slowapi, vollständige OpenAPI-Dokumentation.",
  },
];

function FeatureCard({
  icon,
  title,
  description,
  accent,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  accent: "blue" | "green";
}) {
  const iconBg = accent === "blue" ? "bg-accent-muted text-accent border-accent/20" : "bg-ai-muted text-ai border-ai/20";
  return (
    <div className="group rounded-xl border border-border bg-surface p-5 shadow-sm transition-shadow hover:shadow-md">
      <div className={`mb-3 flex h-10 w-10 items-center justify-center rounded-lg border ${iconBg}`}>
        {icon}
      </div>
      <h3 className="mb-1.5 text-sm font-semibold text-foreground">{title}</h3>
      <p className="text-xs leading-relaxed text-muted-foreground">{description}</p>
    </div>
  );
}

export function FeatureHighlights() {
  return (
    <section className="w-full max-w-4xl mx-auto px-6 py-14">
      {/* Clinical features */}
      <div className="mb-12">
        <div className="mb-6 flex items-center gap-3">
          <span className="flex items-center gap-1.5 rounded-full border border-accent/20 bg-accent-muted px-3 py-1 text-xs font-semibold text-accent-text">
            <svg className="h-3.5 w-3.5" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M8 2a2.5 2.5 0 100 5 2.5 2.5 0 000-5zM4 12c0-2 1.8-3.5 4-3.5s4 1.5 4 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            Klinische Features
          </span>
          <span className="text-xs text-muted-foreground">für Logopäden</span>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {CLINICAL_FEATURES.map(({ icon, title, description }) => (
            <FeatureCard key={title} icon={icon} title={title} description={description} accent="blue" />
          ))}
        </div>
      </div>

      {/* Tech features */}
      <div>
        <div className="mb-6 flex items-center gap-3">
          <span className="flex items-center gap-1.5 rounded-full border border-ai/20 bg-ai-muted px-3 py-1 text-xs font-semibold text-ai-text">
            <svg className="h-3.5 w-3.5" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <rect x="2" y="2" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
              <rect x="9" y="2" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
              <rect x="2" y="9" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
              <rect x="9" y="9" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
            </svg>
            Tech Features
          </span>
          <span className="text-xs text-muted-foreground">für Entwickler</span>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {TECH_FEATURES.map(({ icon, title, description }) => (
            <FeatureCard key={title} icon={icon} title={title} description={description} accent="green" />
          ))}
        </div>
      </div>
    </section>
  );
}
