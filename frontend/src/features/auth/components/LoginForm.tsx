"use client";

import { useState } from "react";
import Link from "next/link";
import { useLogin } from "../hooks/useLogin";
import { TwoFactorChallenge } from "./TwoFactorChallenge";

export function LoginForm() {
  const { submit, submit2fa, loading, error } = useLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [challengeId, setChallengeId] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const res = await submit(email, password);
    if (!res) return;
    if ("step" in res && res.step === "2fa_required") {
      setChallengeId(res.challenge_id);
      return;
    }
    window.location.href = "/";
  }

  async function handle2fa(code: string) {
    if (!challengeId) return;
    const res = await submit2fa(challengeId, code);
    if (res && !("step" in res)) {
      window.location.href = "/";
    }
  }

  if (challengeId) {
    return (
      <TwoFactorChallenge
        onSubmit={handle2fa}
        loading={loading}
        error={error}
      />
    );
  }

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <h1 className="text-2xl font-semibold mb-6">Anmelden</h1>
      <label className="block">
        <span className="text-sm font-medium">Email</span>
        <input
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mt-1 block w-full rounded border border-neutral-300 dark:border-neutral-700 px-3 py-2 bg-white dark:bg-neutral-900"
        />
      </label>
      <label className="block">
        <span className="text-sm font-medium">Passwort</span>
        <input
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
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
        disabled={loading}
        className="w-full rounded bg-blue-600 text-white py-2 disabled:opacity-50"
      >
        Anmelden
      </button>
      <div className="flex justify-between text-sm">
        <Link href="/register" className="text-blue-600 hover:underline">
          Registrieren
        </Link>
        <Link
          href="/forgot-password"
          className="text-blue-600 hover:underline"
        >
          Passwort vergessen?
        </Link>
      </div>
    </form>
  );
}
