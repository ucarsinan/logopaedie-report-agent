"use client";

import { useDemoMode } from "@/hooks/useDemoMode";

export function DemoBanner() {
  const { isDemo } = useDemoMode();

  if (!isDemo) return null;

  return (
    <div className="bg-ai-muted border-b border-ai-text/20 px-4 py-2 text-center text-sm">
      <span className="text-ai-text font-medium">
        ⬡ Demo-Modus · Kein Account erforderlich
      </span>
    </div>
  );
}
