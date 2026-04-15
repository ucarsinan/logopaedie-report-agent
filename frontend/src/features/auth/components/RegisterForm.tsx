"use client";

import { useState } from "react";
import Link from "next/link";
import { useRegister } from "../hooks/useRegister";
import { PasswordStrengthMeter } from "./PasswordStrengthMeter";

export function RegisterForm() {
  const { submit, loading, error, done } = useRegister();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const tooShort = password.length < 12;

  if (done) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Fast geschafft</h1>
        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          Ihre Email-Adresse muss noch bestätigt werden. Bitte prüfen Sie Ihr
          Postfach und klicken Sie den Link in unserer Email.
        </p>
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
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        if (!tooShort) submit(email, password);
      }}
    >
      <h1 className="text-2xl font-semibold mb-6">Registrieren</h1>
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
        <span className="text-sm font-medium">Passwort (min. 12 Zeichen)</span>
        <input
          type="password"
          autoComplete="new-password"
          required
          minLength={12}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mt-1 block w-full rounded border border-neutral-300 dark:border-neutral-700 px-3 py-2 bg-white dark:bg-neutral-900"
        />
        <PasswordStrengthMeter password={password} />
      </label>
      {error && (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={loading || tooShort}
        className="w-full rounded bg-blue-600 text-white py-2 disabled:opacity-50"
      >
        Registrieren
      </button>
    </form>
  );
}
