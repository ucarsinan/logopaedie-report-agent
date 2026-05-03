import Link from "next/link";
import { TypingDemo } from "./TypingDemo";

export function HeroSection() {
  return (
    <section className="flex flex-col items-center gap-8 px-6 py-16 text-center sm:py-24">
      {/* Tech badge */}
      <div className="flex items-center gap-2 rounded-full border border-ai-text/30 bg-ai-muted px-4 py-1.5">
        <span className="h-2 w-2 animate-pulse rounded-full bg-ai" />
        <span className="text-xs font-semibold text-ai-text">
          Groq · Whisper large-v3 · Llama-3.3-70b
        </span>
      </div>

      {/* Headline */}
      <div className="max-w-2xl">
        <h1 className="text-4xl font-bold leading-tight tracking-tight text-foreground sm:text-5xl">
          Weniger Dokumentation.{" "}
          <span className="text-accent">Mehr Therapie.</span>
        </h1>
        <p className="mt-4 text-base text-muted-foreground">
          KI-gestützte klinische Dokumentation für Logopäden
        </p>
      </div>

      {/* CTAs */}
      <div className="flex flex-wrap items-center justify-center gap-3">
        <Link
          href="/module/report?demo=true"
          className="rounded-lg bg-accent px-6 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-accent-hover"
        >
          ▶ Demo starten — ohne Login
        </Link>
        <Link
          href="/login"
          className="rounded-lg border border-border px-6 py-3 text-sm font-semibold text-foreground transition-colors hover:bg-surface"
        >
          Anmelden →
        </Link>
      </div>

      {/* Typing demo */}
      <div className="w-full max-w-xl">
        <TypingDemo />
      </div>
    </section>
  );
}
