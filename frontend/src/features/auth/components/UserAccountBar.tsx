"use client";

import { useState } from "react";
import { useAuth } from "@/features/auth/hooks/useAuth";

const ROLE_LABELS = {
  admin: "Admin",
  user: "Benutzer",
} as const;

function getInitial(email: string): string {
  return email.trim().charAt(0).toUpperCase() || "?";
}

export function UserAccountBar() {
  const { state, logout } = useAuth();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  if (state.status === "loading") {
    return (
      <div
        aria-label="Benutzerstatus wird geladen"
        className="h-8 w-36 rounded-full border border-border bg-surface-elevated"
      />
    );
  }

  if (state.status !== "authenticated") {
    return null;
  }

  const { user } = state;
  const roleLabel = ROLE_LABELS[user.role];

  async function handleLogout() {
    setIsLoggingOut(true);
    await logout();
    window.location.href = "/login";
  }

  return (
    <div
      aria-label="Angemeldeter Benutzer"
      className="flex min-w-0 items-center gap-2 rounded-full border border-border bg-surface px-2 py-1 text-xs shadow-sm"
    >
      <span
        aria-hidden="true"
        className="grid size-7 shrink-0 place-items-center rounded-full bg-accent-muted font-semibold text-accent-text"
      >
        {getInitial(user.email)}
      </span>
      <div className="min-w-0 leading-tight">
        <div className="truncate font-medium text-foreground max-w-[11rem] sm:max-w-[14rem]">
          {user.email}
        </div>
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <span>{roleLabel}</span>
          <span aria-hidden="true">·</span>
          <span>{user.totp_enabled ? "2FA aktiv" : "2FA aus"}</span>
        </div>
      </div>
      <button
        type="button"
        onClick={handleLogout}
        disabled={isLoggingOut}
        className="ml-1 shrink-0 rounded-full border border-border px-2.5 py-1 font-medium text-muted-foreground transition-colors hover:border-border-strong hover:text-foreground disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isLoggingOut ? "..." : "Abmelden"}
      </button>
    </div>
  );
}
