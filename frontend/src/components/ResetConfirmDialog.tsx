"use client";

import { useEffect } from "react";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSoftReset: () => void;
  onFullReset: () => void;
  isSending: boolean;
}

export function ResetConfirmDialog({
  isOpen,
  onClose,
  onSoftReset,
  onFullReset,
  isSending,
}: Props) {
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center"
      onClick={() => { if (!isSending) onClose(); }}
    >
      <div
        className="bg-background border border-border rounded-lg shadow-lg p-6 max-w-sm w-full mx-4"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="reset-dialog-title"
        aria-describedby="reset-dialog-desc"
        onClick={(e) => e.stopPropagation()}
      >
        <h2
          id="reset-dialog-title"
          className="text-lg font-semibold text-foreground mb-2"
        >
          Sitzung zurücksetzen?
        </h2>
        <p id="reset-dialog-desc" className="text-sm text-muted-foreground mb-6">
          Nicht gespeicherte Daten gehen verloren.
        </p>

        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            disabled={isSending}
            className="px-3 py-1.5 rounded text-sm font-medium transition-colors border border-border text-foreground hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            Abbrechen
          </button>
          <button
            onClick={onSoftReset}
            disabled={isSending}
            className="px-3 py-1.5 rounded text-sm font-medium transition-colors border border-red-300 text-red-600 hover:bg-red-50 dark:hover:bg-red-950 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            Neues Gespräch
          </button>
          <button
            onClick={onFullReset}
            disabled={isSending}
            className="px-3 py-1.5 rounded text-sm font-medium transition-colors bg-red-600 hover:bg-red-700 text-white disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            Neue Sitzung
          </button>
        </div>
      </div>
    </div>
  );
}
