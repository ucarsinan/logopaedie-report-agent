"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatMsg } from "@/types";
import { api } from "@/lib/api";
import { ChatBubble, TypingIndicator } from "@/features/chat/components/ChatBubble";
import { ChatInput } from "@/features/chat/components/ChatInput";
import { AnamnesisProgress } from "@/features/chat/components/AnamnesisProgress";
import { WelcomeScreen } from "@/features/chat/components/WelcomeScreen";

const DASH = /[–-]/; // en-dash or hyphen

// Detect option lists in two formats:
//   one-line: "– Option1 – Option2 – Option3"
//   multi-line: consecutive lines each starting with "– Option"
function parseOptions(content: string): string[] {
  const lines = content.split("\n");

  // One-line format (preferred after prompt change)
  for (const line of [...lines].reverse()) {
    const t = line.trim();
    if (new RegExp(`^${DASH.source}\\s+.+(\\s+${DASH.source}\\s+.+)+$`).test(t)) {
      const parts = t.split(/\s*[–-]\s*/).filter(Boolean);
      if (parts.length >= 2 && parts.every((p) => p.length < 80)) return parts;
    }
  }

  // Multi-line format: find the largest consecutive block of "– X" lines
  let best: string[] = [];
  let current: string[] = [];
  for (const line of lines) {
    const t = line.trim();
    if (new RegExp(`^${DASH.source}\\s+\\S`).test(t)) {
      const opt = t.replace(/^[–-]\s+/, "").trim();
      if (opt.length < 80) { current.push(opt); continue; }
    }
    if (current.length > best.length) best = current;
    current = [];
  }
  if (current.length > best.length) best = current;
  return best.length >= 2 ? best : [];
}

function stripOptionsLine(content: string): string {
  const lines = content.split("\n");
  const result: string[] = [];
  let i = 0;
  while (i < lines.length) {
    const t = lines[i].trim();
    // Strip one-line format
    if (new RegExp(`^${DASH.source}\\s+.+(\\s+${DASH.source}\\s+.+)+$`).test(t)) {
      i++; continue;
    }
    // Strip consecutive multi-line block (≥2 lines)
    if (new RegExp(`^${DASH.source}\\s+\\S`).test(t)) {
      let j = i;
      while (j < lines.length && new RegExp(`^${DASH.source}\\s+\\S`).test(lines[j].trim())) j++;
      if (j - i >= 2) { i = j; continue; }
    }
    result.push(lines[i]);
    i++;
  }
  return result.join("\n").trimEnd();
}

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
  setError: React.Dispatch<React.SetStateAction<string | null>>;
  onGenerateReport: () => void;
  onRequestReset: () => void;
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
  setError,
  onGenerateReport,
  onRequestReset,
}: ChatViewProps) {
  const chatEndRef = useRef<HTMLDivElement>(null);
  const [hasStarted, setHasStarted] = useState(false);

  // Show welcome screen only when greeting phase + no user messages yet
  const showWelcome = currentPhase === "greeting" && inputMode === "select" && !hasStarted;

  // Derive quick-reply chips from the last assistant message
  const lastAssistantIdx = messages.reduce<number>(
    (last, m, i) => (m.role === "assistant" ? i : last),
    -1,
  );
  const lastAssistantMsg = lastAssistantIdx >= 0 ? messages[lastAssistantIdx] : null;
  const quickReplies =
    !isSending && lastAssistantMsg ? parseOptions(lastAssistantMsg.content) : [];
  const cleanedLastContent =
    quickReplies.length > 0 && lastAssistantMsg
      ? stripOptionsLine(lastAssistantMsg.content)
      : null;

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!sessionId || !text.trim()) return;
      setError(null);
      setIsSending(true);
      setMessages((prev) => [...prev, { role: "user", content: text }]);

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
    [sessionId, setError, setIsSending, setMessages, setCurrentPhase, setIsAnamnesisComplete, setCollectedFields, setMissingFields],
  );

  const handleSelectReportType = useCallback(
    (type: string) => {
      setInputMode("guided");
      setHasStarted(true);
      sendMessage(type);
    },
    [setInputMode, sendMessage],
  );

  const handleFreeTextSend = useCallback(
    (text: string) => {
      if (!hasStarted) {
        setInputMode("free");
        setHasStarted(true);
      }
      sendMessage(text);
    },
    [hasStarted, setInputMode, sendMessage],
  );

  // Contextual placeholder
  const inputPlaceholder = showWelcome
    ? "Oder beschreiben Sie Ihren Fall frei\u2026"
    : "Ihre Antwort eingeben\u2026";

  return (
    <div className="flex flex-1 flex-col gap-3">
      {/* Header with progress — only after conversation started */}
      {!showWelcome && currentPhase !== "greeting" && (
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <AnamnesisProgress currentPhase={currentPhase} />
            <button
              onClick={onRequestReset}
              className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-muted-foreground hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
              aria-label="Sitzung abbrechen und neu starten"
              title="Sitzung abbrechen und neu starten"
            >
              <svg aria-hidden="true" className="size-3" viewBox="0 0 16 16" fill="currentColor">
                <path fillRule="evenodd" d="M8 15A7 7 0 1 0 8 1a7 7 0 0 0 0 14Zm2.78-4.22a.75.75 0 0 1-1.06 0L8 9.06l-1.72 1.72a.75.75 0 1 1-1.06-1.06L6.94 8 5.22 6.28a.75.75 0 0 1 1.06-1.06L8 6.94l1.72-1.72a.75.75 0 1 1 1.06 1.06L9.06 8l1.72 1.72a.75.75 0 0 1 0 1.06Z" clipRule="evenodd" />
              </svg>
              Abbrechen
            </button>
          </div>
          {missingFields.length > 0 ? (
            <span className="text-xs text-muted-foreground">
              {missingFields.length} Pflichtfelder offen
            </span>
          ) : collectedFields.length > 0 ? (
            <span className="text-xs text-accent">
              Alle Pflichtfelder erfasst
            </span>
          ) : null}
        </div>
      )}

      {/* Welcome screen OR chat messages */}
      {showWelcome ? (
        <WelcomeScreen onSelectReportType={handleSelectReportType} />
      ) : (
        <div className="flex-1 flex flex-col gap-4 overflow-y-auto max-h-[60vh] rounded-xl bg-surface/30 p-4">
          {messages.map((msg, i) => (
            <ChatBubble
              key={i}
              role={msg.role}
              content={
                i === lastAssistantIdx && cleanedLastContent
                  ? cleanedLastContent
                  : msg.content
              }
            />
          ))}
          {quickReplies.length > 0 && (
            <div className="flex flex-wrap gap-2 pl-10 -mt-1">
              {quickReplies.map((opt) => (
                <button
                  key={opt}
                  onClick={() => handleFreeTextSend(opt)}
                  className="rounded-full border border-accent/40 bg-accent-muted px-3.5 py-1.5 text-sm text-accent-text transition-colors hover:bg-accent/15 active:scale-95"
                >
                  {opt}
                </button>
              ))}
            </div>
          )}
          {isSending && <TypingIndicator />}
          <div ref={chatEndRef} />
        </div>
      )}

      {/* Anamnesis complete banner */}
      {isAnamnesisComplete && (
        <div className="flex items-center justify-between rounded-xl border border-accent/30 bg-accent/5 px-4 py-3">
          <span className="text-sm text-foreground">
            Anamnese abgeschlossen — Bericht kann generiert werden.
          </span>
          <button
            onClick={onGenerateReport}
            className="shrink-0 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover transition-colors"
          >
            Bericht generieren
          </button>
        </div>
      )}

      {/* Unified input — always visible */}
      <ChatInput
        onSend={handleFreeTextSend}
        onError={(msg) => setError(msg)}
        disabled={isSending}
        placeholder={inputPlaceholder}
        showAttachment={showWelcome}
      />
    </div>
  );
}
