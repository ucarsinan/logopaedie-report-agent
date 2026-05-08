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
  const dialogRef = useRef<HTMLDivElement>(null);
  const previouslyFocused = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;

    previouslyFocused.current = document.activeElement as HTMLElement | null;

    const getFocusable = () => {
      const root = dialogRef.current;
      if (!root) return [] as HTMLElement[];
      return Array.from(
        root.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      );
    };

    const focusables = getFocusable();
    focusables[0]?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onDismiss();
        return;
      }
      if (e.key !== "Tab") return;
      const items = getFocusable();
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      const active = document.activeElement as HTMLElement | null;
      if (e.shiftKey) {
        if (active === first || !dialogRef.current?.contains(active)) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (active === last) {
          e.preventDefault();
          first.focus();
        }
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
      aria-labelledby="patient-picker-title"
    >
      <div
        ref={dialogRef}
        className="mx-4 max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg border border-border bg-background p-6 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <h2
          id="patient-picker-title"
          className="text-lg font-semibold text-foreground mb-4"
        >
          Patient auswählen
        </h2>
        <PatientSelector onSelect={onSelect} onDemo={onDismiss} />
      </div>
    </div>
  );
}
