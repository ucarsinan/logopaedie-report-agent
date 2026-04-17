"use client";

import { useState } from "react";
import { authApi } from "@/features/auth/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    await authApi.requestPasswordReset(email).catch(() => {});
    setLoading(false);
    setSent(true);
  }

  if (sent) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Email versendet</h1>
        <p className="text-sm">
          Wenn ein Konto mit dieser Email existiert, haben wir einen
          Zurücksetzen-Link gesendet.
        </p>
      </div>
    );
  }

  return (
    <form className="space-y-4" onSubmit={onSubmit}>
      <h1 className="text-2xl font-semibold mb-6">Passwort vergessen</h1>
      <label className="block">
        <span className="text-sm font-medium">Email</span>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mt-1 block w-full rounded border border-neutral-300 dark:border-neutral-700 px-3 py-2 bg-white dark:bg-neutral-900"
        />
      </label>
      <button
        type="submit"
        disabled={loading}
        className="w-full rounded bg-blue-600 text-white py-2 disabled:opacity-50"
      >
        Link senden
      </button>
    </form>
  );
}
