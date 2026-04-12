"use client";

import { useState } from "react";
import { useAudioRecording } from "@/hooks/useAudioRecording";
import { api } from "@/lib/api";
import { MicIcon, StopIcon } from "@/components/icons";

interface DictationButtonProps {
  onTranscript: (text: string) => void;
  disabled?: boolean;
}

export function DictationButton({ onTranscript, disabled }: DictationButtonProps) {
  const [isPending, setIsPending] = useState(false);
  const { isRecording, startRecording, stopRecording } = useAudioRecording({
    onResult: async (blob) => {
      setIsPending(true);
      try {
        const data = await api.transcribe(blob);
        if (data.transcript) onTranscript(data.transcript);
      } finally {
        setIsPending(false);
      }
    },
  });

  if (isPending) {
    return (
      <button disabled className="px-3 py-2 rounded-lg bg-surface-elevated text-foreground/40 text-sm">
        {"\u23f3"}
      </button>
    );
  }

  return isRecording ? (
    <button
      onClick={stopRecording}
      className="px-3 py-2 rounded-lg bg-red-600 text-white motion-safe:animate-pulse text-sm"
      title="Aufnahme stoppen"
    >
      <StopIcon />
    </button>
  ) : (
    <button
      onClick={startRecording}
      disabled={disabled}
      className="px-3 py-2 rounded-lg bg-surface-elevated hover:bg-border-strong text-foreground/80 transition-colors disabled:opacity-40 disabled:cursor-not-allowed text-sm"
      aria-label="Diktieren"
      title="Diktieren"
    >
      <MicIcon />
    </button>
  );
}
