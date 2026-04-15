"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { authApi } from "@/features/auth/api";
import { PasswordStrengthMeter } from "@/features/auth/components/PasswordStrengthMeter";

export default function ResetPasswordPage() {
  const params = useSearchParams();
  const token = params.get("token") ?? "";
  const [pw1, setPw1] = useState("");
  const [pw2, setPw2] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const valid = pw1.length >= 12 && pw1 === pw2 && token;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!valid) return;
    setLoading(true);
    setError(null);
    try {
      await authApi.confirmPasswordReset(token, pw1);
      setDone(true);
    } catch {
      setError("Der Link ist ungültig oder abgelaufen.");
    } finally {
      setLoading(false);
    }
  }

  if (done) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Passwort geändert</h1>
        <Link
          href="/login"
          className="block text-center rounded bg-blue-600 text-white py-2"
        >
          Zur Anmeldung
        </Link>
      </div>
    );
  }

  return (
    <form className="space-y-4" onSubmit={onSubmit}>
      <h1 className="text-2xl font-semibold mb-6">Neues Passwort setzen</h1>
      <div className="block">
        <label htmlFor="pw1" className="text-sm font-medium">
          Neues Passwort
        </label>
        <input
          id="pw1"
          type="password"
          autoComplete="new-password"
          required
          value={pw1}
          onChange={(e) => setPw1(e.target.value)}
          className="mt-1 block w-full rounded border border-neutral-300 dark:border-neutral-700 px-3 py-2 bg-white dark:bg-neutral-900"
        />
        <PasswordStrengthMeter password={pw1} />
      </div>
      <label className="block">
        <span className="text-sm font-medium">Passwort bestätigen</span>
        <input
          type="password"
          autoComplete="new-password"
          required
          value={pw2}
          onChange={(e) => setPw2(e.target.value)}
          className="mt-1 block w-full rounded border border-neutral-300 dark:border-neutral-700 px-3 py-2 bg-white dark:bg-neutral-900"
        />
      </label>
      {error && (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={loading || !valid}
        className="w-full rounded bg-blue-600 text-white py-2 disabled:opacity-50"
      >
        Passwort zurücksetzen
      </button>
    </form>
  );
}
