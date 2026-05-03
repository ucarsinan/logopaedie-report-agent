"use client";

import { useEffect, useState } from "react";

const DEMO_TEXT =
  "Befundbericht: Die Patientin (6 Jahre) zeigt phonologische Auffälligkeiten. Dokumentierte Prozesse: Plosivierung (/f/ → /p/, /v/ → /b/) sowie Fronting (/k/ → /t/, /g/ → /d/). Spontansprache zu 70% verständlich. Empfehlung: Phonologische Therapie 2× wöchentlich, Fokus auf Korrektheit der Frikative.";

export function TypingDemo() {
  const [displayed, setDisplayed] = useState("");
  const [index, setIndex] = useState(0);
  const [pausing, setPausing] = useState(false);

  useEffect(() => {
    if (pausing) {
      const id = setTimeout(() => {
        setDisplayed("");
        setIndex(0);
        setPausing(false);
      }, 2000);
      return () => clearTimeout(id);
    }

    if (index >= DEMO_TEXT.length) {
      setPausing(true);
      return;
    }

    const id = setTimeout(() => {
      setDisplayed((prev) => prev + DEMO_TEXT[index]);
      setIndex((i) => i + 1);
    }, 25);

    return () => clearTimeout(id);
  }, [index, pausing]);

  return (
    <div className="rounded-lg border border-ai-text/20 bg-ai-muted p-4 text-left">
      <div className="mb-2 flex items-center gap-2">
        <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-ai" />
        <span className="text-xs font-semibold text-ai-text">
          ⬡ KI generiert gerade · Llama-3.3-70b
        </span>
      </div>
      <p className="text-sm leading-relaxed text-foreground">
        {displayed}
        <span className="ml-0.5 inline-block h-4 w-0.5 animate-[blink_1s_step-end_infinite] bg-ai align-middle" />
      </p>
    </div>
  );
}
