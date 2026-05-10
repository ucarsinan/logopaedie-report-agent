import Link from "next/link";
import { TypingDemo } from "./TypingDemo";

function WaveformIcon() {
  return (
    <svg
      viewBox="0 0 80 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="h-10 w-20"
      aria-hidden="true"
    >
      <rect x="0" y="16" width="4" height="8" rx="2" fill="currentColor" opacity="0.4" />
      <rect x="8" y="10" width="4" height="20" rx="2" fill="currentColor" opacity="0.6" />
      <rect x="16" y="4" width="4" height="32" rx="2" fill="currentColor" />
      <rect x="24" y="8" width="4" height="24" rx="2" fill="currentColor" opacity="0.8" />
      <rect x="32" y="14" width="4" height="12" rx="2" fill="currentColor" opacity="0.5" />
      <rect x="40" y="6" width="4" height="28" rx="2" fill="currentColor" />
      <rect x="48" y="10" width="4" height="20" rx="2" fill="currentColor" opacity="0.7" />
      <rect x="56" y="4" width="4" height="32" rx="2" fill="currentColor" opacity="0.9" />
      <rect x="64" y="12" width="4" height="16" rx="2" fill="currentColor" opacity="0.5" />
      <rect x="72" y="16" width="4" height="8" rx="2" fill="currentColor" opacity="0.3" />
    </svg>
  );
}

function CheckIcon({ green }: { green?: boolean }) {
  return (
    <svg
      className={`h-4 w-4 shrink-0 ${green ? "text-ai" : "text-accent"}`}
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="8" cy="8" r="7" fill="currentColor" opacity="0.15" />
      <path
        d="M5 8l2 2 4-4"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

const LOGOPAEDIE_BENEFITS = [
  "Befundberichte in unter 2 Minuten",
  "SOAP-Notes automatisch strukturiert",
  "Phonologische Analyse auf Knopfdruck",
];

const TECH_BENEFITS = [
  "FastAPI + Next.js 16 + Groq",
  "Multi-user Auth mit TOTP 2FA",
  "Open Source auf GitHub",
];

export function HeroSection() {
  return (
    <section className="relative overflow-hidden px-6 pb-16 pt-14 sm:pt-20">
      {/* Gradient background */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 bg-linear-to-b from-accent-muted/60 via-background to-background"
      />
      {/* Subtle grid overlay */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 opacity-[0.025]"
        style={{
          backgroundImage:
            "linear-gradient(var(--color-foreground) 1px, transparent 1px), linear-gradient(90deg, var(--color-foreground) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />

      <div className="mx-auto flex max-w-5xl flex-col items-center gap-10 text-center">
        {/* Dual-audience badges */}
        <div className="flex flex-wrap items-center justify-center gap-2">
          <span className="flex items-center gap-1.5 rounded-full border border-accent/20 bg-accent-muted px-3.5 py-1 text-xs font-semibold text-accent-text">
            <svg className="h-3.5 w-3.5" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path
                d="M8 2a2.5 2.5 0 100 5 2.5 2.5 0 000-5zM4 12c0-2 1.8-3.5 4-3.5s4 1.5 4 3.5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
            Für Logopäden
          </span>
          <span className="text-muted-foreground/30">·</span>
          <span className="flex items-center gap-1.5 rounded-full border border-ai/20 bg-ai-muted px-3.5 py-1 text-xs font-semibold text-ai-text">
            <svg className="h-3.5 w-3.5" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <rect x="2" y="2" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
              <rect x="9" y="2" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
              <rect x="2" y="9" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
              <rect x="9" y="9" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
            </svg>
            Für Entwickler
          </span>
        </div>

        {/* Waveform icon */}
        <div className="flex items-center justify-center rounded-2xl border border-accent/15 bg-accent-muted/50 p-4 text-accent shadow-sm">
          <WaveformIcon />
        </div>

        {/* Headline */}
        <div className="max-w-2xl">
          <h1 className="text-4xl font-extrabold leading-tight tracking-tight text-foreground sm:text-5xl">
            <span className="block">Weniger Dokumentation.</span>
            <span className="block text-accent">Mehr Therapie.</span>
          </h1>
          <p className="mt-4 text-base leading-relaxed text-muted-foreground sm:text-lg">
            KI-gestützte klinische Dokumentation für Logopäden — powered by Groq Whisper &amp;
            Llama-3.3-70b. Moderner Open-Source-Stack für Entwickler.
          </p>
        </div>

        {/* CTAs */}
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/module/report?demo=true"
            className="inline-flex items-center gap-2 rounded-lg bg-accent px-6 py-3 text-sm font-semibold text-white shadow-sm transition-all hover:bg-accent-hover hover:shadow-md focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
          >
            <svg className="h-4 w-4" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" />
              <path d="M6.5 5.5l4 2.5-4 2.5V5.5z" fill="currentColor" />
            </svg>
            Demo starten — ohne Login
          </Link>
          <Link
            href="/login"
            className="inline-flex items-center gap-2 rounded-lg border border-border bg-background px-6 py-3 text-sm font-semibold text-foreground transition-all hover:border-border-strong hover:bg-surface focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
          >
            Anmelden
            <svg className="h-4 w-4" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path
                d="M3 8h10M9 4l4 4-4 4"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </Link>
        </div>

        {/* Dual benefit columns */}
        <div className="grid w-full max-w-2xl grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="rounded-xl border border-accent/15 bg-accent-muted/40 p-4 text-left">
            <p className="mb-2.5 text-xs font-semibold uppercase tracking-wide text-accent-text">
              Klinische Features
            </p>
            <ul className="flex flex-col gap-1.5">
              {LOGOPAEDIE_BENEFITS.map((b) => (
                <li key={b} className="flex items-start gap-2 text-xs text-foreground/80">
                  <CheckIcon />
                  {b}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-xl border border-ai/15 bg-ai-muted/40 p-4 text-left">
            <p className="mb-2.5 text-xs font-semibold uppercase tracking-wide text-ai-text">
              Tech Stack
            </p>
            <ul className="flex flex-col gap-1.5">
              {TECH_BENEFITS.map((b) => (
                <li key={b} className="flex items-start gap-2 text-xs text-foreground/80">
                  <CheckIcon green />
                  {b}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Typing demo */}
        <div className="w-full max-w-xl">
          <TypingDemo />
        </div>
      </div>
    </section>
  );
}
