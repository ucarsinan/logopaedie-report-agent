"use client";

import { useRef, useState } from "react";

interface MedicalReport {
  patient_pseudonym: string;
  symptoms: string[];
  therapy_progress: string;
  prognosis: string;
}

async function uploadAudio(
  audioBlob: Blob,
  setReport: (r: MedicalReport) => void,
  setError: (e: string) => void,
  setIsProcessing: (v: boolean) => void
) {
  setIsProcessing(true);
  setError("");

  const formData = new FormData();
  // Backend parameter name is `audio_file` (defined in main.py: audio_file: UploadFile)
  formData.append("audio_file", audioBlob, "recording.webm");

  try {
    const apiBase =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const res = await fetch(`${apiBase}/process-audio`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const detail = await res.json().catch(() => null);
      throw new Error(
        detail?.detail ?? `Server-Fehler: ${res.status} ${res.statusText}`
      );
    }

    const data = (await res.json()) as MedicalReport;
    setReport(data);
  } catch (err) {
    setError(err instanceof Error ? err.message : "Unbekannter Fehler.");
  } finally {
    setIsProcessing(false);
  }
}

export default function Home() {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [report, setReport] = useState<MedicalReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  async function startRecording() {
    setError(null);
    setReport(null);
    audioChunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        // Release the microphone immediately
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        uploadAudio(blob, setReport, (e) => setError(e), setIsProcessing);
      };

      recorder.start();
      setIsRecording(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Mikrofon-Zugriff verweigert oder nicht verfügbar."
      );
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col">
      {/* Header */}
      <header className="border-b border-zinc-800 px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-3">
          <span className="text-lg font-semibold tracking-tight">
            Logopädie Report Agent
          </span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 font-mono">
            v0.2 · live
          </span>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-12 flex flex-col gap-10">
        {/* Title */}
        <section className="flex flex-col gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">
            Medizinischen Bericht erstellen
          </h1>
          <p className="text-zinc-400 text-sm leading-relaxed">
            Nehmen Sie die Therapiesitzung auf. Die KI transkribiert das Audio
            und generiert einen strukturierten Arztbericht.
          </p>
        </section>

        {/* Recording controls */}
        <section className="flex flex-col gap-4">
          {!isRecording ? (
            <button
              onClick={startRecording}
              disabled={isProcessing}
              className="w-full sm:w-auto self-start inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white font-medium text-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              aria-label="Aufnahme starten"
            >
              <MicIcon />
              Aufnahme starten
            </button>
          ) : (
            <button
              onClick={stopRecording}
              className="w-full sm:w-auto self-start inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-red-600 text-white font-medium text-sm motion-safe:animate-pulse"
              aria-label="Stop und Analysieren"
            >
              <StopIcon />
              Stop &amp; Analysieren
            </button>
          )}

          {isRecording && (
            <p className="flex items-center gap-2 text-sm text-red-400">
              <span className="w-2 h-2 rounded-full bg-red-500 motion-safe:animate-ping inline-block" />
              Aufnahme läuft…
            </p>
          )}
        </section>

        {/* Processing state */}
        {isProcessing && (
          <section
            aria-live="polite"
            className="flex items-center gap-3 rounded-lg bg-zinc-900 border border-zinc-800 px-5 py-4 text-sm text-zinc-300"
          >
            <Spinner />
            Analysiere Audio und generiere Arztbericht…
          </section>
        )}

        {/* Error */}
        {error && (
          <section
            role="alert"
            className="rounded-lg bg-red-950 border border-red-800 px-5 py-4 text-sm text-red-300 flex items-start gap-3"
          >
            <AlertIcon />
            <span>{error}</span>
          </section>
        )}

        {/* Report */}
        {report && <ReportCard report={report} />}
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-800 px-6 py-4 text-center text-xs text-zinc-600">
        Zero-Cost Architecture · Groq API · FastAPI + Next.js
      </footer>
    </div>
  );
}

/* ─────────────────────────── Report Card ─────────────────────────── */

function ReportCard({ report }: { report: MedicalReport }) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-widest">
        Generierter Arztbericht
      </h2>

      <div className="rounded-lg border border-zinc-800 overflow-hidden divide-y divide-zinc-800">
        {/* Patient pseudonym */}
        <div className="px-5 py-4 flex items-center gap-3 bg-zinc-900">
          <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider w-28 shrink-0">
            Patient
          </span>
          <span className="font-mono text-indigo-300 text-sm">
            {report.patient_pseudonym}
          </span>
        </div>

        {/* Symptoms */}
        <div className="px-5 py-4 bg-zinc-900/60">
          <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-3">
            Symptome
          </p>
          <ul className="flex flex-col gap-1.5">
            {report.symptoms.map((s, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-sm text-zinc-200"
              >
                <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-indigo-500 shrink-0" />
                {s}
              </li>
            ))}
          </ul>
        </div>

        {/* Therapy progress */}
        <div className="px-5 py-4 bg-zinc-900/60">
          <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
            Therapieverlauf
          </p>
          <p className="text-sm text-zinc-200 leading-relaxed">
            {report.therapy_progress}
          </p>
        </div>

        {/* Prognosis */}
        <div className="px-5 py-4 bg-zinc-900/60">
          <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
            Prognose
          </p>
          <p className="text-sm text-zinc-200 leading-relaxed">
            {report.prognosis}
          </p>
        </div>
      </div>
    </section>
  );
}

/* ─────────────────────────── Icons / Spinner ─────────────────────── */

function MicIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      className="w-4 h-4"
      aria-hidden="true"
    >
      <path d="M8.25 4.5a3.75 3.75 0 1 1 7.5 0v8.25a3.75 3.75 0 1 1-7.5 0V4.5Z" />
      <path d="M6 10.5a.75.75 0 0 1 .75.75v1.5a5.25 5.25 0 1 0 10.5 0v-1.5a.75.75 0 0 1 1.5 0v1.5a6.751 6.751 0 0 1-6 6.709v2.291h3a.75.75 0 0 1 0 1.5h-7.5a.75.75 0 0 1 0-1.5h3v-2.291a6.751 6.751 0 0 1-6-6.709v-1.5A.75.75 0 0 1 6 10.5Z" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      className="w-4 h-4"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M4.5 7.5a3 3 0 0 1 3-3h9a3 3 0 0 1 3 3v9a3 3 0 0 1-3 3h-9a3 3 0 0 1-3-3v-9Z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      className="w-4 h-4 shrink-0 mt-0.5 text-red-400"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M9.401 3.003c1.155-2 4.043-2 5.197 0l7.355 12.748c1.154 2-.29 4.5-2.599 4.5H4.645c-2.309 0-3.752-2.5-2.598-4.5L9.4 3.003ZM12 8.25a.75.75 0 0 1 .75.75v3.75a.75.75 0 0 1-1.5 0V9a.75.75 0 0 1 .75-.75Zm0 8.25a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function Spinner() {
  return (
    <svg
      className="w-4 h-4 motion-safe:animate-spin text-indigo-400 shrink-0"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4Z"
      />
    </svg>
  );
}
