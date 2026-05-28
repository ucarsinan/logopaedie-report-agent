"use client";

import { createContext, useCallback, useContext, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import {
  SESSION_STORAGE_KEY,
  STALE_SESSION_TOAST,
  clearStoredSession,
  isStaleSessionError,
} from "@/lib/stale-session";
import type { ChatMsg } from "@/types";

interface SessionContextValue {
  sessionId: string | null;
  setSessionId: (id: string | null) => void;
  messages: ChatMsg[];
  setMessages: React.Dispatch<React.SetStateAction<ChatMsg[]>>;
  isSending: boolean;
  setIsSending: React.Dispatch<React.SetStateAction<boolean>>;
  error: string | null;
  setError: React.Dispatch<React.SetStateAction<string | null>>;
  handleSoftReset: () => Promise<void>;
  handleFullReset: () => Promise<void>;
  /**
   * Drop the stored/active session id and notify the user.
   * Call from a `catch` after detecting a stale-session 404
   * via `isStaleSessionError(err)`.
   */
  handleStaleSession: () => void;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStaleSession = useCallback(() => {
    clearStoredSession();
    setSessionId(null);
    setMessages([]);
    toast.error(STALE_SESSION_TOAST);
  }, []);

  const handleSoftReset = useCallback(async () => {
    if (!sessionId) return;
    setIsSending(true);
    setError(null);
    try {
      const data = await api.sessions.newConversation(sessionId);
      setMessages(
        data.collected_data?.greeting
          ? [{ role: "assistant", content: data.collected_data.greeting }]
          : [],
      );
      const resetFn = (window as unknown as Record<string, unknown>).__reportModuleReset;
      if (typeof resetFn === "function") (resetFn as () => void)();
    } catch (err) {
      if (isStaleSessionError(err)) {
        handleStaleSession();
        return;
      }
      setError(err instanceof Error ? err.message : "Unbekannter Fehler.");
    } finally {
      setIsSending(false);
    }
  }, [sessionId, handleStaleSession]);

  const handleFullReset = useCallback(async () => {
    setIsSending(true);
    setError(null);
    try {
      const data = await api.sessions.create();
      setSessionId(data.session_id);
      localStorage.setItem(SESSION_STORAGE_KEY, data.session_id);
      setMessages(
        data.collected_data?.greeting
          ? [{ role: "assistant", content: data.collected_data.greeting }]
          : [],
      );
      const resetFn = (window as unknown as Record<string, unknown>).__reportModuleReset;
      if (typeof resetFn === "function") (resetFn as () => void)();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unbekannter Fehler.");
    } finally {
      setIsSending(false);
    }
  }, []);

  return (
    <SessionContext.Provider
      value={{
        sessionId,
        setSessionId,
        messages,
        setMessages,
        isSending,
        setIsSending,
        error,
        setError,
        handleSoftReset,
        handleFullReset,
        handleStaleSession,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used within SessionProvider");
  return ctx;
}
