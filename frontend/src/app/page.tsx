import Link from "next/link";
import { BrandLogo } from "@/components/BrandLogo";
import { HeroSection } from "@/components/landing/HeroSection";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { FeatureHighlights } from "@/components/landing/FeatureHighlights";
import { ScreenshotSection } from "@/components/landing/ScreenshotSection";
import { ArchitectureCallout } from "@/components/landing/ArchitectureCallout";
import { RecentReportsSection } from "@/components/landing/RecentReportsSection";

const GITHUB_URL = "https://github.com/ucarsinan/logopaedie-report-agent";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
          <Link href="/" className="flex items-center gap-3">
            <BrandLogo compact />
            <span className="text-sm font-semibold text-foreground">
              Logopädie Report Agent
            </span>
          </Link>
          <div className="flex items-center gap-3">
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              GitHub ★
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
      </main>

      {/* Footer */}
      <footer className="border-t border-border px-6 py-4 text-center text-xs text-muted">
        Logopädie Report Agent · Groq API · FastAPI + Next.js ·{" "}
        <a
          href={GITHUB_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="text-accent-text hover:underline"
        >
          GitHub
        </a>
        {" · "}
        <Link href="/login" className="text-accent-text hover:underline">
          Anmelden
        </Link>
      </footer>
    </div>
  );
}
