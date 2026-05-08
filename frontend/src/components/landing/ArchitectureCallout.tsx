import { GITHUB_URL } from "@/lib/constants";

const STATS = ["157 Backend-Tests", "9 API-Router", "Fernet-encrypted Sessions"];

export function ArchitectureCallout() {
  return (
    <section className="w-full max-w-4xl mx-auto px-6 py-12">
      <div className="flex flex-col items-center gap-6 rounded-xl border border-border bg-card p-8 text-center shadow-sm">
        <div>
          <h2 className="text-lg font-semibold text-foreground">
            Gebaut für den Praxiseinsatz
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Vollständiger Quellcode auf GitHub
          </p>
        </div>
        <div className="flex flex-wrap justify-center gap-3">
          {STATS.map((label) => (
            <span
              key={label}
              className="rounded-full border border-accent/30 bg-accent-muted px-4 py-1.5 text-xs font-semibold text-accent-text"
            >
              {label}
            </span>
          ))}
        </div>
        <a
          href={GITHUB_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-lg border border-border px-5 py-2.5 text-sm font-semibold text-foreground transition-colors hover:bg-surface"
        >
          GitHub ansehen →
        </a>
      </div>
    </section>
  );
}
