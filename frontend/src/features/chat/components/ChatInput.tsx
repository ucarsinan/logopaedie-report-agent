"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAudioRecording } from "@/hooks/useAudioRecording";
import { api } from "@/lib/api";
import { MicIcon, StopIcon } from "@/components/icons";

interface ChatInputProps {
  onSend: (text: string) => void;
  onFileSelect?: (files: FileList) => void;
  onError?: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  showAttachment?: boolean;
}

export function ChatInput({
  onSend,
  onFileSelect,
  onError,
  disabled = false,
  placeholder = "Ihre Antwort eingeben\u2026",
  showAttachment = false,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const [isTranscribing, setIsTranscribing] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { isRecording, startRecording, stopRecording } = useAudioRecording({
    onResult: async (blob) => {
      setIsTranscribing(true);
      try {
        const data = await api.transcribe(blob);
        if (data.transcript) {
          setValue((prev) => (prev ? prev + " " + data.transcript! : data.transcript!));
          textareaRef.current?.focus();
        } else {
          onError?.("Keine Sprache erkannt. Bitte erneut aufnehmen.");
        }
      } catch (err) {
        onError?.(
          err instanceof Error
            ? `Transkription fehlgeschlagen: ${err.message}`
            : "Transkription fehlgeschlagen. Bitte erneut versuchen.",
        );
      } finally {
        setIsTranscribing(false);
      }
    },
  });

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 128) + "px";
  }, [value]);

  // Cmd+K focus
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        textareaRef.current?.focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [value, disabled, onSend]);

  return (
    <div className="relative flex items-end gap-2 rounded-2xl border border-border-strong bg-surface px-3 py-2 transition-colors focus-within:border-accent/50 print:hidden">
      {/* Attachment button */}
      {showAttachment && onFileSelect && (
        <>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
            className="flex size-9 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-surface-elevated transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            aria-label="Datei anhängen"
            title="Datei anhängen"
          >
            <svg aria-hidden="true" className="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48" />
            </svg>
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.txt"
            onChange={(e) => {
              if (e.target.files?.length) onFileSelect(e.target.files);
              e.target.value = "";
            }}
            className="hidden"
          />
        </>
      )}

      {/* Textarea */}
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
          }
        }}
        disabled={disabled}
        placeholder={placeholder}
        rows={1}
        className="flex-1 resize-none bg-transparent py-1.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none disabled:opacity-40"
      />

      {/* Mic button */}
      {isTranscribing ? (
        <button
          disabled
          className="flex size-9 shrink-0 items-center justify-center rounded-lg text-muted-foreground/40 disabled:cursor-not-allowed"
          aria-label="Sprachaufnahme wird transkribiert"
          title="Transkribiert\u2026"
        >
          <svg aria-hidden="true" className="size-4 animate-spin motion-reduce:animate-none" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4Z" />
          </svg>
        </button>
      ) : !isRecording ? (
        <button
          type="button"
          onClick={startRecording}
          disabled={disabled}
          className="flex size-9 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-surface-elevated transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          aria-label="Sprachaufnahme starten"
          title="Spracheingabe"
        >
          <MicIcon />
        </button>
      ) : (
        <button
          type="button"
          onClick={stopRecording}
          className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-red-500 text-white animate-pulse motion-reduce:animate-none"
          aria-label="Aufnahme stoppen"
          title="Aufnahme stoppen"
        >
          <StopIcon />
        </button>
      )}

      {/* Send button */}
      <button
        type="button"
        onClick={handleSubmit}
        disabled={disabled || isTranscribing || !value.trim()}
        className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent text-white transition-colors hover:bg-accent-hover disabled:opacity-30 disabled:cursor-not-allowed"
        aria-label="Nachricht senden"
        title="Senden"
      >
        <svg aria-hidden="true" className="size-4" viewBox="0 0 24 24" fill="currentColor">
          <path d="M3.478 2.404a.75.75 0 0 0-.926.941l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.404Z" />
        </svg>
      </button>
      {isTranscribing && (
        <span role="status" aria-live="polite" className="sr-only">
          Transkribiert…
        </span>
      )}
    </div>
  );
}
