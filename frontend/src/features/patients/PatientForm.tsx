"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { CreatePatientRequest, Patient, UpdatePatientRequest } from "@/types";

type PatientFormProps = {
  patientId?: string;
};

type FormState = {
  realname: string;
  birthdate: string;
  pseudonym: string;
  phone: string;
  email: string;
  insurance_nr: string;
  gender: string;
  age_group: string;
  icd10_codes: string;
  disorder_text: string;
  indikationsschluessel: string;
  insurance_type: string;
  insurance_name: string;
  guardian_name: string;
};

const EMPTY_FORM: FormState = {
  realname: "",
  birthdate: "",
  pseudonym: "",
  phone: "",
  email: "",
  insurance_nr: "",
  gender: "",
  age_group: "erwachsen",
  icd10_codes: "",
  disorder_text: "",
  indikationsschluessel: "",
  insurance_type: "",
  insurance_name: "",
  guardian_name: "",
};

function toFormState(patient: Patient): FormState {
  return {
    realname: patient.realname,
    birthdate: patient.birthdate,
    pseudonym: patient.pseudonym,
    phone: patient.phone ?? "",
    email: patient.email ?? "",
    insurance_nr: patient.insurance_nr ?? "",
    gender: patient.gender ?? "",
    age_group: patient.age_group,
    icd10_codes: patient.icd10_codes.join(", "),
    disorder_text: patient.disorder_text,
    indikationsschluessel: patient.indikationsschluessel,
    insurance_type: patient.insurance_type ?? "",
    insurance_name: patient.insurance_name ?? "",
    guardian_name: patient.guardian_name ?? "",
  };
}

function optional(value: string): string | null {
  const trimmed = value.trim();
  return trimmed || null;
}

function parseCodes(value: string): string[] {
  return value
    .split(",")
    .map((code) => code.trim())
    .filter(Boolean);
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-sm">
      <span className="font-medium text-foreground">{label}</span>
      {children}
    </label>
  );
}

const inputClass =
  "min-h-10 rounded-md border border-border bg-input px-3 text-sm text-foreground outline-none transition-colors placeholder:text-muted focus:border-accent focus:ring-2 focus:ring-ring/20 disabled:cursor-not-allowed disabled:opacity-60";

export function PatientForm({ patientId }: PatientFormProps) {
  const router = useRouter();
  const isEdit = Boolean(patientId);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!patientId) return;
    setLoading(true);
    api.patients
      .get(patientId)
      .then((patient) => setForm(toFormState(patient)))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [patientId]);

  const title = isEdit ? "Patient bearbeiten" : "Patient anlegen";
  const canSubmit = useMemo(
    () =>
      isEdit ||
      (form.realname.trim().length > 0 && form.birthdate.trim().length > 0),
    [form.birthdate, form.realname, isEdit],
  );

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);

    try {
      if (patientId) {
        const payload: UpdatePatientRequest = {
          pseudonym: optional(form.pseudonym),
          phone: optional(form.phone),
          email: optional(form.email),
          gender: optional(form.gender),
          age_group: optional(form.age_group),
          icd10_codes: parseCodes(form.icd10_codes),
          disorder_text: form.disorder_text,
          indikationsschluessel: form.indikationsschluessel,
          insurance_type: optional(form.insurance_type),
          insurance_name: optional(form.insurance_name),
          guardian_name: optional(form.guardian_name),
        };
        const saved = await api.patients.update(patientId, payload);
        router.push(`/patienten/${saved.id}`);
        return;
      }

      const payload: CreatePatientRequest = {
        realname: form.realname.trim(),
        birthdate: form.birthdate.trim(),
        pseudonym: optional(form.pseudonym),
        phone: optional(form.phone),
        email: optional(form.email),
        insurance_nr: optional(form.insurance_nr),
        gender: optional(form.gender),
        age_group: form.age_group,
        icd10_codes: parseCodes(form.icd10_codes),
        disorder_text: form.disorder_text,
        indikationsschluessel: form.indikationsschluessel,
        insurance_type: optional(form.insurance_type),
        insurance_name: optional(form.insurance_name),
        guardian_name: optional(form.guardian_name),
      };
      const created = await api.patients.create(payload);
      router.push(`/patienten/${created.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Speichern fehlgeschlagen.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-6 py-8">
      <div className="flex flex-col gap-3 border-b border-border pb-5">
        <Link
          href="/patienten"
          className="text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          ← Zurück zur Patientenliste
        </Link>
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent-text">
            Patientenverwaltung
          </p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">
            {title}
          </h1>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-error-border bg-error-surface px-4 py-3 text-sm text-error-text">
          {error}
        </div>
      )}

      {loading ? (
        <div className="rounded-lg border border-border bg-card px-4 py-10 text-center text-sm text-muted-foreground">
          Lade Patientendaten...
        </div>
      ) : (
        <form
          onSubmit={handleSubmit}
          className="grid gap-6 rounded-lg border border-border bg-card p-4 md:p-5"
        >
          <section className="grid gap-4 md:grid-cols-2">
            <Field label="Realname">
              <input
                value={form.realname}
                onChange={(event) => update("realname", event.target.value)}
                disabled={isEdit}
                required={!isEdit}
                className={inputClass}
              />
            </Field>
            <Field label="Geburtsdatum">
              <input
                type="date"
                value={form.birthdate}
                onChange={(event) => update("birthdate", event.target.value)}
                disabled={isEdit}
                required={!isEdit}
                className={inputClass}
              />
            </Field>
            <Field label="Pseudonym">
              <input
                value={form.pseudonym}
                onChange={(event) => update("pseudonym", event.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label="Altersgruppe">
              <select
                value={form.age_group}
                onChange={(event) => update("age_group", event.target.value)}
                className={inputClass}
              >
                <option value="kind">Kind</option>
                <option value="jugendlich">Jugendlich</option>
                <option value="erwachsen">Erwachsen</option>
              </select>
            </Field>
            <Field label="Geschlecht">
              <select
                value={form.gender}
                onChange={(event) => update("gender", event.target.value)}
                className={inputClass}
              >
                <option value="">Keine Angabe</option>
                <option value="weiblich">Weiblich</option>
                <option value="männlich">Männlich</option>
                <option value="divers">Divers</option>
              </select>
            </Field>
            <Field label="Sorgeberechtigte">
              <input
                value={form.guardian_name}
                onChange={(event) => update("guardian_name", event.target.value)}
                className={inputClass}
              />
            </Field>
          </section>

          <section className="grid gap-4 border-t border-border pt-5 md:grid-cols-2">
            <Field label="Telefon">
              <input
                value={form.phone}
                onChange={(event) => update("phone", event.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label="E-Mail">
              <input
                type="email"
                value={form.email}
                onChange={(event) => update("email", event.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label="Versichertennummer">
              <input
                value={form.insurance_nr}
                onChange={(event) => update("insurance_nr", event.target.value)}
                disabled={isEdit}
                className={inputClass}
              />
            </Field>
            <Field label="Versicherungstyp">
              <select
                value={form.insurance_type}
                onChange={(event) => update("insurance_type", event.target.value)}
                className={inputClass}
              >
                <option value="">Keine Angabe</option>
                <option value="GKV">GKV</option>
                <option value="PKV">PKV</option>
              </select>
            </Field>
            <Field label="Krankenkasse">
              <input
                value={form.insurance_name}
                onChange={(event) => update("insurance_name", event.target.value)}
                className={inputClass}
              />
            </Field>
          </section>

          <section className="grid gap-4 border-t border-border pt-5 md:grid-cols-2">
            <Field label="ICD-10 Codes">
              <input
                value={form.icd10_codes}
                onChange={(event) => update("icd10_codes", event.target.value)}
                placeholder="F80.0, F80.1"
                className={inputClass}
              />
            </Field>
            <Field label="Indikationsschlüssel">
              <input
                value={form.indikationsschluessel}
                onChange={(event) =>
                  update("indikationsschluessel", event.target.value)
                }
                placeholder="SP1"
                className={inputClass}
              />
            </Field>
            <label className="flex flex-col gap-1.5 text-sm md:col-span-2">
              <span className="font-medium text-foreground">Störungsbild</span>
              <textarea
                value={form.disorder_text}
                onChange={(event) => update("disorder_text", event.target.value)}
                rows={4}
                className="rounded-md border border-border bg-input px-3 py-2 text-sm text-foreground outline-none transition-colors placeholder:text-muted focus:border-accent focus:ring-2 focus:ring-ring/20"
              />
            </label>
          </section>

          <div className="flex flex-col-reverse gap-2 border-t border-border pt-5 sm:flex-row sm:justify-end">
            <Link
              href="/patienten"
              className="inline-flex min-h-10 items-center justify-center rounded-md border border-border px-4 text-sm font-medium text-foreground transition-colors hover:bg-surface"
            >
              Abbrechen
            </Link>
            <button
              type="submit"
              disabled={!canSubmit || saving}
              className="inline-flex min-h-10 items-center justify-center rounded-md bg-accent px-4 text-sm font-semibold text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              {saving ? "Speichert..." : "Speichern"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
