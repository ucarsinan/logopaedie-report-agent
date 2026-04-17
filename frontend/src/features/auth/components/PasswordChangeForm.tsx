"use client";

import { useState } from "react";
import { authApi } from "@/features/auth/api";

export function PasswordChangeForm() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const valid = next.length >= 12;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!valid) return;
    setLoading(true);
    setError(null);
    try {
      await authApi.changePassword(current, next);
      setDone(true);
      setCurrent("");
      setNext("");
    } catch {
      setError("Änderung fehlgeschlagen.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="space-y-4" onSubmit={onSubmit}>
      <label className="block">
        <span className="text-sm font-medium">Aktuelles Passwort</span>
        <input
          type="password"
          autoComplete="current-password"
          required
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          className="mt-1 block w-full rounded border border-neutral-300 dark:border-neutral-700 px-3 py-2 bg-white dark:bg-neutral-900"
        />
      </label>
      <label className="block">
        <span className="text-sm font-medium">Neues Passwort</span>
        <input
          type="password"
          autoComplete="new-password"
          required
          minLength={12}
          value={next}
          onChange={(e) => setNext(e.target.value)}
          className="mt-1 block w-full rounded border border-neutral-300 dark:border-neutral-700 px-3 py-2 bg-white dark:bg-neutral-900"
        />
      </label>
      {done && <p className="text-sm text-green-600">Passwort geändert.</p>}
      {error && (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={loading || !valid}
        className="rounded bg-blue-600 text-white px-4 py-2 disabled:opacity-50"
      >
        Passwort ändern
      </button>
    </form>
  );
}
