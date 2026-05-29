"use client";

import { useEffect, useState } from "react";

const DEMO_TEXT =
  "Befundbericht: Die Patientin (6 Jahre) zeigt phonologische Auffälligkeiten. Dokumentierte Prozesse: Plosivierung (/f/ → /p/, /v/ → /b/) sowie Fronting (/k/ → /t/, /g/ → /d/). Spontansprache zu 70% verständlich. Empfehlung: Phonologische Therapie 2× wöchentlich, Fokus auf Korrektheit der Frikative.";

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function TypingDemo() {
  const [reducedMotion] = useState<boolean>(() => prefersReducedMotion());
  const [displayed, setDisplayed] = useState<string>(() =>
    prefersReducedMotion() ? DEMO_TEXT : "",
  );
  const [index, setIndex] = useState<number>(() =>
    prefersReducedMotion() ? DEMO_TEXT.length : 0,
  );

  useEffect(() => {
    if (reducedMotion) return;

    if (index >= DEMO_TEXT.length) {
      const id = setTimeout(() => {
        setDisplayed("");
        setIndex(0);
      }, 2000);
      return () => clearTimeout(id);
    }

    const id = setTimeout(() => {
      setDisplayed((prev) => prev + DEMO_TEXT[index]);
      setIndex((i) => i + 1);
    }, 25);

    return () => clearTimeout(id);
  }, [index, reducedMotion]);

  return (
    <div className="rounded-lg border border-ai-text/20 bg-ai-muted p-4 text-left">
      <div className="mb-2 flex items-center gap-2">
        <span className="inline-block h-2 w-2 animate-pulse motion-reduce:animate-none rounded-full bg-ai" />
        <span className="text-xs font-semibold text-ai-text">
          ⬡ KI generiert gerade · Llama-3.3-70b
        </span>
      </div>
      <div className="relative text-sm leading-relaxed text-foreground">
        <p className="invisible select-none" aria-hidden="true">{DEMO_TEXT}</p>
        <p className="absolute inset-0">{displayed}<span className="ml-0.5 inline-block h-4 w-0.5 animate-[blink_1s_step-end_infinite] motion-reduce:animate-none bg-ai align-middle" /></p>
      </div>
    </div>
  );
}
