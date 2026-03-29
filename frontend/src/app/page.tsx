"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/* ═══════════════════════════════════ Types ═══════════════════════════════════ */

interface ChatMsg {
  role: "user" | "assistant";
  content: string;
}

interface ChatResponse {
  message: string;
  phase: string;
  is_anamnesis_complete: boolean;
  collected_fields: string[];
}

interface UploadedFile {
  filename: string;
  material_type: string;
  extracted_text: string;
}

interface DiagnoseData {
  icd_10_codes: string[];
  indikationsschluessel: string;
  diagnose_text: string;
}

interface PatientData {
  pseudonym: string;
  age_group: string;
  gender: string | null;
}

// Union report shape – fields vary by report_type
interface ReportData {
  report_type: string;
  patient: PatientData;
  diagnose: DiagnoseData;
  // befundbericht
  anamnese?: string;
  befund?: string;
  therapieindikation?: string;
  therapieziele?: string[];
  empfehlung?: string;
  // therapiebericht_kurz
  empfehlungen?: string;
  // therapiebericht_lang
  therapeutische_diagnostik?: string;
  aktueller_krankheitsstatus?: string;
  aktueller_therapiestand?: string;
  weiteres_vorgehen?: string;
  // abschlussbericht
  therapieverlauf_zusammenfassung?: string;
  ergebnis?: string;
}

type AppPhase = "chat" | "upload" | "generating" | "preview";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ═══════════════════════════════ Main Component ═════════════════════════════ */

export default function Home() {
  const [phase, setPhase] = useState<AppPhase>("chat");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isAnamnesisComplete, setIsAnamnesisComplete] = useState(false);
  const [collectedFields, setCollectedFields] = useState<string[]>([]);
  const [currentPhase, setCurrentPhase] = useState("greeting");
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [report, setReport] = useState<ReportData | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Audio recording
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Create session on mount ────────────────────────────────────────
  useEffect(() => {
    async function init() {
      try {
        const res = await fetch(`${API}/sessions`, { method: "POST" });
        if (!res.ok) throw new Error("Session konnte nicht erstellt werden.");
        const data = await res.json();
        setSessionId(data.session_id);
        if (data.collected_data?.greeting) {
          setMessages([
            { role: "assistant", content: data.collected_data.greeting },
          ]);
        }
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Verbindung fehlgeschlagen."
        );
      }
    }
    init();
  }, []);

  // ── Send text message ──────────────────────────────────────────────
  const sendMessage = useCallback(
    async (text: string) => {
      if (!sessionId || !text.trim()) return;
      setError(null);
      setIsSending(true);
      setMessages((prev) => [...prev, { role: "user", content: text }]);
      setInput("");

      try {
        const res = await fetch(`${API}/sessions/${sessionId}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text }),
        });
        if (!res.ok) {
          const detail = await res.json().catch(() => null);
          throw new Error(detail?.detail ?? "Fehler beim Senden.");
        }
        const data: ChatResponse = await res.json();
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.message },
        ]);
        setCurrentPhase(data.phase);
        setIsAnamnesisComplete(data.is_anamnesis_complete);
        setCollectedFields(data.collected_fields);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unbekannter Fehler.");
      } finally {
        setIsSending(false);
      }
    },
    [sessionId]
  );

  // ── Audio recording ────────────────────────────────────────────────
  async function startRecording() {
    setError(null);
    audioChunksRef.current = [];
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        sendAudio(blob);
      };
      recorder.start();
      setIsRecording(true);
    } catch {
      setError("Mikrofon-Zugriff verweigert oder nicht verfügbar.");
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  }

  async function sendAudio(blob: Blob) {
    if (!sessionId) return;
    setIsSending(true);
    setError(null);
    setMessages((prev) => [
      ...prev,
      { role: "user", content: "🎤 Sprachnachricht wird verarbeitet…" },
    ]);

    const formData = new FormData();
    formData.append("audio_file", blob, "recording.webm");

    try {
      const res = await fetch(`${API}/sessions/${sessionId}/audio`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail ?? "Audio-Verarbeitung fehlgeschlagen.");
      }
      const data: ChatResponse = await res.json();
      // Replace placeholder with transcript indication
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: "user", content: prev[prev.length - 1].content.replace("🎤 Sprachnachricht wird verarbeitet…", "🎤 (Sprachnachricht)") },
        { role: "assistant", content: data.message },
      ]);
      setCurrentPhase(data.phase);
      setIsAnamnesisComplete(data.is_anamnesis_complete);
      setCollectedFields(data.collected_fields);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unbekannter Fehler.");
    } finally {
      setIsSending(false);
    }
  }

  // ── File upload ────────────────────────────────────────────────────
  async function handleFileUpload(files: FileList) {
    if (!sessionId) return;
    setError(null);

    for (const file of Array.from(files)) {
      const formData = new FormData();
      formData.append("file", file);

      try {
        const res = await fetch(
          `${API}/sessions/${sessionId}/upload?material_type=sonstiges`,
          { method: "POST", body: formData }
        );
        if (!res.ok) {
          const detail = await res.json().catch(() => null);
          throw new Error(detail?.detail ?? `Upload von ${file.name} fehlgeschlagen.`);
        }
        const data = await res.json();
        setUploadedFiles((prev) => [...prev, data]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload fehlgeschlagen.");
      }
    }
  }

  // ── Generate report ────────────────────────────────────────────────
  async function generateReport() {
    if (!sessionId) return;
    setPhase("generating");
    setError(null);

    try {
      const res = await fetch(`${API}/sessions/${sessionId}/generate`, {
        method: "POST",
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail ?? "Berichtgenerierung fehlgeschlagen.");
      }
      const data = await res.json();
      setReport(data);
      setPhase("preview");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unbekannter Fehler.");
      setPhase("upload");
    }
  }

  // ── Render ─────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col">
      {/* Header */}
      <header className="border-b border-zinc-800 px-6 py-4 print:hidden">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-lg font-semibold tracking-tight">
              Logopädie Report Agent
            </span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 font-mono">
              v1.0
            </span>
          </div>
          {/* Phase indicator */}
          <nav className="flex items-center gap-1 text-xs">
            <PhaseStep
              label="Anamnese"
              active={phase === "chat"}
              done={phase !== "chat"}
            />
            <ChevronRight />
            <PhaseStep
              label="Materialien"
              active={phase === "upload"}
              done={phase === "generating" || phase === "preview"}
            />
            <ChevronRight />
            <PhaseStep
              label="Bericht"
              active={phase === "generating" || phase === "preview"}
              done={phase === "preview"}
            />
          </nav>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-4xl mx-auto w-full px-6 py-8 flex flex-col gap-6">
        {/* Error */}
        {error && (
          <div
            role="alert"
            className="rounded-lg bg-red-950 border border-red-800 px-5 py-4 text-sm text-red-300 flex items-start gap-3 print:hidden"
          >
            <AlertIcon />
            <span>{error}</span>
          </div>
        )}

        {/* ── Phase: Chat ────────────────────────────────────────── */}
        {phase === "chat" && (
          <>
            <div className="flex items-center justify-between">
              <h1 className="text-xl font-semibold tracking-tight">
                Anamnese-Gespräch
              </h1>
              {collectedFields.length > 0 && (
                <span className="text-xs text-zinc-500">
                  {collectedFields.length} Felder erfasst
                </span>
              )}
            </div>

            {/* Chat messages */}
            <div className="flex-1 flex flex-col gap-3 overflow-y-auto max-h-[60vh] rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
              {messages.map((msg, i) => (
                <ChatBubble key={i} role={msg.role} content={msg.content} />
              ))}
              {isSending && (
                <div className="flex items-center gap-2 text-sm text-zinc-500">
                  <Spinner /> Antwort wird generiert…
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Input area */}
            <div className="flex gap-2 print:hidden">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage(input);
                  }
                }}
                disabled={isSending}
                placeholder="Ihre Antwort eingeben…"
                className="flex-1 rounded-lg bg-zinc-900 border border-zinc-700 px-4 py-3 text-sm placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 disabled:opacity-40"
              />
              {!isRecording ? (
                <button
                  onClick={startRecording}
                  disabled={isSending}
                  className="px-4 py-3 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 transition-colors disabled:opacity-40"
                  title="Spracheingabe"
                >
                  <MicIcon />
                </button>
              ) : (
                <button
                  onClick={stopRecording}
                  className="px-4 py-3 rounded-lg bg-red-600 text-white motion-safe:animate-pulse"
                  title="Aufnahme stoppen"
                >
                  <StopIcon />
                </button>
              )}
              <button
                onClick={() => sendMessage(input)}
                disabled={isSending || !input.trim()}
                className="px-6 py-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-colors disabled:opacity-40"
              >
                Senden
              </button>
            </div>

            {/* Transition to upload */}
            {isAnamnesisComplete && (
              <div className="flex items-center gap-3 rounded-lg bg-indigo-950/50 border border-indigo-800 px-5 py-4">
                <span className="text-sm text-indigo-300">
                  Anamnese abgeschlossen! Sie können jetzt Materialien
                  hochladen oder direkt den Bericht generieren.
                </span>
                <button
                  onClick={() => setPhase("upload")}
                  className="shrink-0 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
                >
                  Weiter
                </button>
              </div>
            )}
          </>
        )}

        {/* ── Phase: Upload ──────────────────────────────────────── */}
        {phase === "upload" && (
          <>
            <div className="flex items-center justify-between">
              <h1 className="text-xl font-semibold tracking-tight">
                Materialien hochladen
              </h1>
              <button
                onClick={() => setPhase("chat")}
                className="text-sm text-zinc-500 hover:text-zinc-300"
              >
                ← Zurück zum Gespräch
              </button>
            </div>

            <p className="text-sm text-zinc-400">
              Laden Sie vorhandene Berichte, Diagnostik-Ergebnisse oder
              Verordnungen hoch (PDF, DOCX, TXT). Diese werden als Kontext für
              die Berichterstellung verwendet. Dieser Schritt ist optional.
            </p>

            {/* Drop zone */}
            <DropZone onFiles={handleFileUpload} />

            {/* File list */}
            {uploadedFiles.length > 0 && (
              <div className="flex flex-col gap-2">
                <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-widest">
                  Hochgeladene Dateien
                </h2>
                {uploadedFiles.map((f, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-3 rounded-lg bg-zinc-900 border border-zinc-800 px-4 py-3 text-sm"
                  >
                    <FileIcon />
                    <span className="text-zinc-200">{f.filename}</span>
                    <span className="text-xs text-zinc-600 ml-auto">
                      {f.extracted_text.length} Zeichen extrahiert
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Generate button */}
            <button
              onClick={generateReport}
              className="self-start px-6 py-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-colors"
            >
              Bericht generieren
            </button>
          </>
        )}

        {/* ── Phase: Generating ──────────────────────────────────── */}
        {phase === "generating" && (
          <div className="flex-1 flex flex-col items-center justify-center gap-4">
            <Spinner />
            <p className="text-sm text-zinc-400">
              Bericht wird generiert… Dies kann einen Moment dauern.
            </p>
          </div>
        )}

        {/* ── Phase: Preview ─────────────────────────────────────── */}
        {phase === "preview" && report && (
          <>
            <div className="flex items-center justify-between print:hidden">
              <h1 className="text-xl font-semibold tracking-tight">
                Generierter Bericht
              </h1>
              <div className="flex gap-2">
                <button
                  onClick={() => setPhase("upload")}
                  className="text-sm text-zinc-500 hover:text-zinc-300"
                >
                  ← Zurück
                </button>
                <button
                  onClick={() => window.print()}
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
                >
                  Drucken / PDF
                </button>
              </div>
            </div>
            <ReportPreview report={report} />
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-800 px-6 py-4 text-center text-xs text-zinc-600 print:hidden">
        Logopädie Report Agent · Groq API · FastAPI + Next.js
      </footer>
    </div>
  );
}

/* ═══════════════════════════════ Chat Bubble ═════════════════════════════════ */

function ChatBubble({ role, content }: { role: string; content: string }) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
          isUser
            ? "bg-indigo-600 text-white rounded-br-md"
            : "bg-zinc-800 text-zinc-200 rounded-bl-md"
        }`}
      >
        {content}
      </div>
    </div>
  );
}

/* ═══════════════════════════════ Drop Zone ═══════════════════════════════════ */

function DropZone({ onFiles }: { onFiles: (files: FileList) => void }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragOver(true);
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragOver(false);
        if (e.dataTransfer.files.length) onFiles(e.dataTransfer.files);
      }}
      onClick={() => inputRef.current?.click()}
      className={`flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed px-8 py-12 cursor-pointer transition-colors ${
        isDragOver
          ? "border-indigo-500 bg-indigo-950/30"
          : "border-zinc-700 bg-zinc-900/50 hover:border-zinc-600"
      }`}
    >
      <UploadIcon />
      <p className="text-sm text-zinc-400">
        Dateien hierher ziehen oder <span className="text-indigo-400">durchsuchen</span>
      </p>
      <p className="text-xs text-zinc-600">PDF, DOCX oder TXT · Max. 10 MB</p>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.txt"
        onChange={(e) => {
          if (e.target.files?.length) onFiles(e.target.files);
        }}
        className="hidden"
      />
    </div>
  );
}

/* ═══════════════════════════════ Report Preview ══════════════════════════════ */

function ReportPreview({ report }: { report: ReportData }) {
  const typeLabels: Record<string, string> = {
    befundbericht: "Befundbericht",
    therapiebericht_kurz: "Therapiebericht (kurz) – Verordnungsbericht",
    therapiebericht_lang: "Therapiebericht (lang) – Bericht auf besondere Anforderung",
    abschlussbericht: "Abschlussbericht",
  };

  return (
    <div className="rounded-lg border border-zinc-800 overflow-hidden divide-y divide-zinc-800 print:border-black print:divide-black print:text-black print:bg-white">
      {/* Header */}
      <div className="px-6 py-4 bg-zinc-900 print:bg-white">
        <h2 className="text-lg font-semibold print:text-black">
          {typeLabels[report.report_type] || report.report_type}
        </h2>
      </div>

      {/* Patient & Diagnose */}
      <ReportSection title="Patientendaten">
        <p><strong>Pseudonym:</strong> {report.patient.pseudonym}</p>
        <p><strong>Altersgruppe:</strong> {report.patient.age_group}</p>
        {report.patient.gender && <p><strong>Geschlecht:</strong> {report.patient.gender}</p>}
      </ReportSection>

      <ReportSection title="Diagnose">
        {report.diagnose.indikationsschluessel && (
          <p><strong>Indikationsschlüssel:</strong> {report.diagnose.indikationsschluessel}</p>
        )}
        {report.diagnose.icd_10_codes.length > 0 && (
          <p><strong>ICD-10:</strong> {report.diagnose.icd_10_codes.join(", ")}</p>
        )}
        {report.diagnose.diagnose_text && <p>{report.diagnose.diagnose_text}</p>}
      </ReportSection>

      {/* Type-specific sections */}
      {report.report_type === "befundbericht" && (
        <>
          <ReportSection title="Anamnese">{report.anamnese}</ReportSection>
          <ReportSection title="Befund">{report.befund}</ReportSection>
          <ReportSection title="Therapieindikation">{report.therapieindikation}</ReportSection>
          {report.therapieziele && report.therapieziele.length > 0 && (
            <ReportSection title="Therapieziele">
              <ul className="list-disc list-inside space-y-1">
                {report.therapieziele.map((z, i) => <li key={i}>{z}</li>)}
              </ul>
            </ReportSection>
          )}
          <ReportSection title="Empfehlung">{report.empfehlung}</ReportSection>
        </>
      )}

      {report.report_type === "therapiebericht_kurz" && (
        <ReportSection title="Empfehlungen">{report.empfehlungen}</ReportSection>
      )}

      {report.report_type === "therapiebericht_lang" && (
        <>
          <ReportSection title="Therapeutische Diagnostik">{report.therapeutische_diagnostik}</ReportSection>
          <ReportSection title="Aktueller Krankheitsstatus">{report.aktueller_krankheitsstatus}</ReportSection>
          <ReportSection title="Aktueller Therapiestand">{report.aktueller_therapiestand}</ReportSection>
          <ReportSection title="Weiteres Vorgehen">{report.weiteres_vorgehen}</ReportSection>
        </>
      )}

      {report.report_type === "abschlussbericht" && (
        <>
          <ReportSection title="Therapieverlauf">{report.therapieverlauf_zusammenfassung}</ReportSection>
          <ReportSection title="Ergebnis">{report.ergebnis}</ReportSection>
          <ReportSection title="Empfehlung">{report.empfehlung}</ReportSection>
        </>
      )}
    </div>
  );
}

function ReportSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="px-6 py-4 bg-zinc-900/60 print:bg-white">
      <h3 className="text-xs font-medium text-zinc-500 uppercase tracking-widest mb-2 print:text-black print:font-bold print:text-sm print:normal-case">
        {title}
      </h3>
      <div className="text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap print:text-black">
        {children}
      </div>
    </div>
  );
}

/* ═══════════════════════════════ Phase Step ══════════════════════════════════ */

function PhaseStep({
  label,
  active,
  done,
}: {
  label: string;
  active: boolean;
  done: boolean;
}) {
  return (
    <span
      className={`px-2.5 py-1 rounded-full text-xs font-medium ${
        active
          ? "bg-indigo-600 text-white"
          : done
            ? "bg-green-900 text-green-300"
            : "bg-zinc-800 text-zinc-500"
      }`}
    >
      {done ? "✓ " : ""}
      {label}
    </span>
  );
}

/* ═══════════════════════════════ Icons / Spinner ═════════════════════════════ */

function ChevronRight() {
  return (
    <svg className="w-3 h-3 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
    </svg>
  );
}

function MicIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4" aria-hidden="true">
      <path d="M8.25 4.5a3.75 3.75 0 1 1 7.5 0v8.25a3.75 3.75 0 1 1-7.5 0V4.5Z" />
      <path d="M6 10.5a.75.75 0 0 1 .75.75v1.5a5.25 5.25 0 1 0 10.5 0v-1.5a.75.75 0 0 1 1.5 0v1.5a6.751 6.751 0 0 1-6 6.709v2.291h3a.75.75 0 0 1 0 1.5h-7.5a.75.75 0 0 1 0-1.5h3v-2.291a6.751 6.751 0 0 1-6-6.709v-1.5A.75.75 0 0 1 6 10.5Z" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4" aria-hidden="true">
      <path fillRule="evenodd" d="M4.5 7.5a3 3 0 0 1 3-3h9a3 3 0 0 1 3 3v9a3 3 0 0 1-3 3h-9a3 3 0 0 1-3-3v-9Z" clipRule="evenodd" />
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 shrink-0 mt-0.5 text-red-400" aria-hidden="true">
      <path fillRule="evenodd" d="M9.401 3.003c1.155-2 4.043-2 5.197 0l7.355 12.748c1.154 2-.29 4.5-2.599 4.5H4.645c-2.309 0-3.752-2.5-2.598-4.5L9.4 3.003ZM12 8.25a.75.75 0 0 1 .75.75v3.75a.75.75 0 0 1-1.5 0V9a.75.75 0 0 1 .75-.75Zm0 8.25a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z" clipRule="evenodd" />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-zinc-500">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" />
    </svg>
  );
}

function FileIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4 text-zinc-500">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
    </svg>
  );
}

function Spinner() {
  return (
    <svg className="w-4 h-4 motion-safe:animate-spin text-indigo-400 shrink-0" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4Z" />
    </svg>
  );
}
