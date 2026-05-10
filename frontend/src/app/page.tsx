import Link from "next/link";
import { BrandLogo } from "@/components/BrandLogo";
import { HeroSection } from "@/components/landing/HeroSection";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { FeatureHighlights } from "@/components/landing/FeatureHighlights";
import { ScreenshotSection } from "@/components/landing/ScreenshotSection";
import { ArchitectureCallout } from "@/components/landing/ArchitectureCallout";
import { RecentReportsSection } from "@/components/landing/RecentReportsSection";
import { GITHUB_URL } from "@/lib/constants";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col [font-family:var(--font-display)]">
      {/* Header */}
      <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
          <Link href="/" className="flex items-center gap-2.5">
            <BrandLogo compact />
            <div className="flex flex-col leading-none">
              <span className="text-sm font-semibold text-foreground">
                Logopädie Report Agent
              </span>
              <span className="text-[10px] text-muted-foreground">
                KI-Dokumentation · Open Source
              </span>
            </div>
          </Link>
          <div className="flex items-center gap-3">
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="hidden items-center gap-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground sm:flex"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
              </svg>
              GitHub
            </a>
            <Link
              href="/module/report?demo=true"
              className="rounded-lg bg-accent px-4 py-2 text-xs font-semibold text-white transition-colors hover:bg-accent-hover"
            >
              Demo starten
            </Link>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1">
        <HeroSection />

        <div className="border-t border-border">
          <HowItWorks />
        </div>

        <div className="border-t border-border">
          <RecentReportsSection />
        </div>

        <div className="border-t border-border">
          <FeatureHighlights />
        </div>

        <div className="border-t border-border">
          <ScreenshotSection />
        </div>

        <div className="border-t border-border">
          <ArchitectureCallout />
        </div>

        {/* Final CTA */}
        <div className="border-t border-border">
          <section className="mx-auto max-w-4xl px-6 py-14 text-center">
            <div className="rounded-2xl border border-accent/20 bg-accent-muted/40 px-8 py-10">
              <h2 className="text-2xl font-extrabold text-foreground">
                Jetzt ausprobieren — kostenlos & ohne Login
              </h2>
              <p className="mt-3 text-sm text-muted-foreground">
                Demo-Modus starten und in 2 Minuten einen echten Befundbericht generieren.
              </p>
              <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
                <Link
                  href="/module/report?demo=true"
                  className="inline-flex items-center gap-2 rounded-lg bg-accent px-6 py-3 text-sm font-semibold text-white shadow-sm transition-all hover:bg-accent-hover hover:shadow-md"
                >
                  <svg className="h-4 w-4" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                    <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" />
                    <path d="M6.5 5.5l4 2.5-4 2.5V5.5z" fill="currentColor" />
                  </svg>
                  Demo starten
                </Link>
                <Link
                  href="/login"
                  className="inline-flex items-center gap-2 rounded-lg border border-border bg-background px-6 py-3 text-sm font-semibold text-foreground transition-all hover:bg-surface"
                >
                  Konto erstellen
                </Link>
              </div>
            </div>
          </section>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border">
        <div className="mx-auto max-w-5xl px-6 py-6">
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-between">
            <div className="flex items-center gap-2.5">
              <BrandLogo compact />
              <span className="text-xs font-medium text-muted-foreground">
                Logopädie Report Agent
              </span>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-4 text-xs text-muted-foreground">
              <span>Groq API · FastAPI · Next.js</span>
              <a
                href={GITHUB_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="transition-colors hover:text-foreground"
              >
                GitHub
              </a>
              <Link href="/login" className="transition-colors hover:text-foreground">
                Anmelden
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
