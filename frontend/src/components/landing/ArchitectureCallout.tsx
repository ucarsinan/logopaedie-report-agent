import { GITHUB_URL } from "@/lib/constants";

const STACK_LAYERS = [
  {
    label: "Frontend",
    color: "accent",
    items: ["Next.js 16", "React 19", "Tailwind CSS v4", "TypeScript"],
  },
  {
    label: "Backend",
    color: "ai",
    items: ["FastAPI", "Python 3.12", "Pydantic v2", "SQLModel"],
  },
  {
    label: "KI / Modelle",
    color: "accent",
    items: ["Groq API", "Whisper large-v3", "Llama-3.3-70b", "STT + NLP"],
  },
  {
    label: "Persistenz",
    color: "ai",
    items: ["Neon PostgreSQL", "Upstash Redis", "Fernet-Encryption", "24h TTL"],
  },
];

const STATS = [
  {
    value: "35+",
    label: "Backend Tests",
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M9 12l2 2 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M12 3C7 3 3 7 3 12s4 9 9 9 9-4 9-9-4-9-9-9z" stroke="currentColor" strokeWidth="1.5" />
      </svg>
    ),
  },
  {
    value: "9",
    label: "API Router",
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M4 6h16M4 12h10M4 18h7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        <circle cx="19" cy="17" r="3" stroke="currentColor" strokeWidth="1.5" />
      </svg>
    ),
  },
  {
    value: "4",
    label: "Berichtstypen",
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M14 3H6a2 2 0 00-2 2v14a2 2 0 002 2h12a2 2 0 002-2V9l-6-6z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
        <path d="M14 3v6h6" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
        <path d="M8 13h8M8 17h5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    value: "E2E",
    label: "Playwright Tests",
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <rect x="3" y="3" width="18" height="14" rx="2" stroke="currentColor" strokeWidth="1.5" />
        <path d="M9 21h6M12 17v4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M8 9l2 2 5-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
];

export function ArchitectureCallout() {
  return (
    <section className="w-full max-w-4xl mx-auto px-6 py-14">
      <div className="overflow-hidden rounded-2xl border border-border bg-surface shadow-sm">
        {/* Header */}
        <div className="border-b border-border bg-surface-elevated px-6 py-5">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-base font-bold text-foreground">
                Gebaut für den Praxiseinsatz
              </h2>
              <p className="mt-0.5 text-sm text-muted-foreground">
                Produktionsreifer Stack — vollständig auf GitHub
              </p>
            </div>
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-flex items-center gap-2 rounded-lg border border-border bg-background px-4 py-2 text-xs font-semibold text-foreground transition-colors hover:bg-surface-elevated sm:mt-0"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
              </svg>
              GitHub ansehen
            </a>
          </div>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 divide-x divide-y divide-border sm:grid-cols-4 sm:divide-y-0">
          {STATS.map(({ value, label, icon }) => (
            <div key={label} className="flex flex-col items-center gap-1.5 px-4 py-5">
              <div className="text-accent">{icon}</div>
              <span className="text-xl font-bold text-foreground">{value}</span>
              <span className="text-xs text-muted-foreground">{label}</span>
            </div>
          ))}
        </div>

        {/* Stack grid */}
        <div className="border-t border-border p-6">
          <p className="mb-4 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Tech Stack
          </p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {STACK_LAYERS.map(({ label, color, items }) => (
              <div key={label} className="rounded-lg border border-border bg-background p-3">
                <p
                  className={`mb-2 text-xs font-semibold ${
                    color === "accent" ? "text-accent-text" : "text-ai-text"
                  }`}
                >
                  {label}
                </p>
                <ul className="flex flex-col gap-1">
                  {items.map((item) => (
                    <li
                      key={item}
                      className="flex items-center gap-1.5 text-xs text-muted-foreground"
                    >
                      <span
                        className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                          color === "accent" ? "bg-accent" : "bg-ai"
                        }`}
                      />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Deploy note */}
        <div className="border-t border-border bg-surface-elevated px-6 py-3">
          <p className="text-xs text-muted-foreground">
            Deployed auf{" "}
            <span className="font-semibold text-foreground">Vercel</span> als Monorepo mit{" "}
            <span className="font-mono text-xs text-accent-text">experimentalServices</span>
            {" · "}CI via{" "}
            <span className="font-semibold text-foreground">GitHub Actions</span> (lint, typecheck, test)
          </p>
        </div>
      </div>
    </section>
  );
}
