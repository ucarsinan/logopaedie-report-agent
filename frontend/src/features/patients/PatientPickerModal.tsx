"use client";

import { useEffect, useRef } from "react";
import { PatientSelector } from "@/features/chat/PatientSelector";
import type { PatientSummary } from "@/types";

interface PatientPickerModalProps {
  open: boolean;
  onSelect: (patient: PatientSummary) => void;
  onDismiss: () => void;
}

export function PatientPickerModal({
  open,
  onSelect,
  onDismiss,
}: PatientPickerModalProps) {
  const previouslyFocused = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;

    previouslyFocused.current = document.activeElement as HTMLElement | null;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onDismiss();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previouslyFocused.current?.focus?.();
    };
  }, [open, onDismiss]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      role="dialog"
      aria-modal="true"
      aria-label="Patient auswählen"
    >
      <div
        className="mx-4 max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg border border-border bg-background p-6 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <PatientSelector onSelect={onSelect} onDemo={onDismiss} />
      </div>
    </div>
  );
}
