"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatMsg } from "@/types";
import { api } from "@/lib/api";
import { useAudioRecording } from "@/hooks/useAudioRecording";
import { MicIcon, StopIcon, Spinner } from "@/components/icons";
import { ChatBubble } from "@/features/chat/components/ChatBubble";
import { AnamnesisProgress } from "@/features/chat/components/AnamnesisProgress";
import { QuickReplyBubbles } from "@/features/chat/components/QuickReplyBubbles";
import { ModeSelectionCards } from "@/features/chat/components/ModeSelectionCards";
import { FreeTextInput } from "@/features/chat/components/FreeTextInput";

interface ChatViewProps {
  sessionId: string | null;
  messages: ChatMsg[];
  setMessages: React.Dispatch<React.SetStateAction<ChatMsg[]>>;
  isSending: boolean;
  setIsSending: React.Dispatch<React.SetStateAction<boolean>>;
  isAnamnesisComplete: boolean;
  setIsAnamnesisComplete: React.Dispatch<React.SetStateAction<boolean>>;
  collectedFields: string[];
  setCollectedFields: React.Dispatch<React.SetStateAction<string[]>>;
  missingFields: string[];
  setMissingFields: React.Dispatch<React.SetStateAction<string[]>>;
  currentPhase: string;
  setCurrentPhase: React.Dispatch<React.SetStateAction<string>>;
  inputMode: "select" | "free" | "guided";
  setInputMode: React.Dispatch<React.SetStateAction<"select" | "free" | "guided">>;
  freeText: string;
  setFreeText: React.Dispatch<React.SetStateAction<string>>;
  freeTextReportType: string;
  setFreeTextReportType: React.Dispatch<React.SetStateAction<string>>;
  error: string | null;
  setError: React.Dispatch<React.SetStateAction<string | null>>;
  onGenerateReport: () => void;
}

export function ChatView({
  sessionId,
  messages,
  setMessages,
  isSending,
  setIsSending,
  isAnamnesisComplete,
  setIsAnamnesisComplete,
  collectedFields,
  setCollectedFields,
  missingFields,
  setMissingFields,
  currentPhase,
  setCurrentPhase,
  inputMode,
  setInputMode,
  freeText,
  setFreeText,
  freeTextReportType,
  setFreeTextReportType,
  error: _error,
  setError,
  onGenerateReport,
}: ChatViewProps) {
  const [input, setInput] = useState("");
  const chatEndRef = useRef<HTMLDivElement>(null);
  const chatInputRef = useRef<HTMLInputElement>(null);

  // Audio recording (transcribe-to-text for input field)
  const [isTranscribing, setIsTranscribing] = useState(false);
  const { isRecording, startRecording, stopRecording } = useAudioRecording({
    onResult: async (blob) => {
      setIsTranscribing(true);
      try {
        const data = await api.transcribe(blob);
        if (data.transcript) {
          setInput((prev) => prev ? prev + " " + data.transcript! : data.transcript!);
          chatInputRef.current?.focus();
        }
      } catch {
        setError("Transkription fehlgeschlagen.");
      } finally {
        setIsTranscribing(false);
      }
    },
  });

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Cmd+K focus
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        chatInputRef.current?.focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!sessionId || !text.trim()) return;
      setError(null);
      setIsSending(true);
      setMessages((prev) => [...prev, { role: "user", content: text }]);
      setInput("");

      try {
        const data = await api.sessions.chat(sessionId, text);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.message },
        ]);
        setCurrentPhase(data.phase);
        setIsAnamnesisComplete(data.is_anamnesis_complete);
        setCollectedFields(data.collected_fields);
        setMissingFields(data.missing_fields ?? []);
      } catch (err) {
        setMessages((prev) => prev.slice(0, -1));
        setError(err instanceof Error ? err.message : "Unbekannter Fehler.");
      } finally {
        setIsSending(false);
      }
    },
    [sessionId, setError, setIsSending, setMessages, setCurrentPhase, setIsAnamnesisComplete, setCollectedFields, setMissingFields]
  );

  const sendFreeText = useCallback(async () => {
    if (!freeText.trim() || !freeTextReportType || isSending || !sessionId) return;

    const combinedMessage = `Berichtstyp: ${freeTextReportType}\n\n${freeText}`;

    setIsSending(true);
    setMessages((prev) => [...prev, { role: "user" as const, content: freeText }]);
    setFreeText("");

    try {
      const data = await api.sessions.chat(sessionId, combinedMessage, "quick_input");
      setMessages((prev) => [...prev, { role: "assistant" as const, content: data.message }]);
      setCurrentPhase(data.phase);
      setIsAnamnesisComplete(data.is_anamnesis_complete);
      setCollectedFields(data.collected_fields ?? []);
      setMissingFields(data.missing_fields ?? []);
    } catch (err) {
      setMessages((prev) => prev.slice(0, -1));
      setError(err instanceof Error ? err.message : "Fehler beim Senden. Bitte erneut versuchen.");
    } finally {
      setIsSending(false);
    }
  }, [sessionId, freeText, freeTextReportType, isSending, setIsSending, setMessages, setFreeText, setCurrentPhase, setIsAnamnesisComplete, setCollectedFields, setMissingFields, setError]);

  return (
    <>
      {currentPhase !== "greeting" && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-semibold tracking-tight">
              Anamnese-Gespräch
            </h1>
            {missingFields.length > 0 ? (
              <span className="text-xs text-muted-foreground">
                {missingFields.length} Pflichtfelder offen
              </span>
            ) : collectedFields.length > 0 ? (
              <span className="text-xs" style={{ color: "var(--accent-text)" }}>
                Alle Pflichtfelder erfasst
              </span>
            ) : null}
          </div>
          <AnamnesisProgress currentPhase={currentPhase} />
        </div>
      )}

      {/* Chat messages */}
      <div className="flex-1 flex flex-col gap-3 overflow-y-auto max-h-[60vh] rounded-lg border border-border bg-surface p-4 card-elevated">
        {messages.map((msg, i) => (
          <ChatBubble key={i} role={msg.role} content={msg.content} />
        ))}
        {currentPhase === "greeting" && inputMode === "select" && (
          <ModeSelectionCards onSelect={(mode) => setInputMode(mode)} />
        )}
        {currentPhase === "greeting" && inputMode === "guided" && (
          <QuickReplyBubbles onSelect={sendMessage} disabled={isSending} />
        )}
        {currentPhase === "greeting" && inputMode === "free" && (
          <FreeTextInput
            reportType={freeTextReportType}
            onReportTypeChange={setFreeTextReportType}
            value={freeText}
            onChange={setFreeText}
            onSubmit={sendFreeText}
            disabled={isSending}
          />
        )}
        {isSending && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Spinner /> Antwort wird generiert…
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Input area */}
      {currentPhase !== "greeting" && (
        <div className="flex gap-2 print:hidden">
          <input
            ref={chatInputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage(input);
              }
            }}
            disabled={isSending}
            placeholder="Ihre Antwort eingeben…"
            className="flex-1 rounded-lg bg-input border border-border-strong px-4 py-3 text-sm text-foreground placeholder:text-muted focus:outline-none focus:border-ring disabled:opacity-40"
          />
          {isTranscribing ? (
            <button disabled className="px-4 py-3 rounded-lg bg-surface-elevated text-foreground/40" title="Transkribiert…">
              {"\u23f3"}
            </button>
          ) : !isRecording ? (
            <button
              onClick={startRecording}
              disabled={isSending}
              className="px-4 py-3 rounded-lg bg-surface-elevated hover:bg-border-strong text-foreground/80 transition-colors disabled:opacity-40"
              title="Spracheingabe"
            >
              <MicIcon />
            </button>
          ) : (
            <button
              onClick={stopRecording}
              className="px-4 py-3 rounded-lg bg-red-600 text-white motion-safe:animate-pulse"
              title="Aufnahme stoppen"
            >
              <StopIcon />
            </button>
          )}
          <button
            onClick={() => sendMessage(input)}
            disabled={isSending || isTranscribing || !input.trim()}
            className="px-6 py-3 rounded-lg bg-accent hover:bg-accent-hover text-white font-medium text-sm transition-colors disabled:opacity-40 btn-accent-glow"
          >
            Senden
          </button>
        </div>
      )}

      {/* Transition to generating */}
      {isAnamnesisComplete && (
        <div className="flex items-center gap-3 rounded-lg border border-accent px-5 py-4 bg-accent-muted">
          <span className="text-sm text-accent-text">
            Anamnese abgeschlossen! Sie können den Bericht jetzt generieren.
          </span>
          <button
            onClick={onGenerateReport}
            className="shrink-0 px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors btn-accent-glow"
          >
            Bericht generieren
          </button>
        </div>
      )}
    </>
  );
}
