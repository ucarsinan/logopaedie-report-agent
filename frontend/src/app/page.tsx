"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ThemeToggle } from "@/components/ThemeToggle";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Link from "next/link";

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
type AppModule = "report" | "phonology" | "therapy-plan" | "compare" | "suggest";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ═══════════════════════════ Feature Types ═══════════════════════════════ */

interface PhonologicalProcess {
  target_word: string;
  production: string;
  processes: string[];
  severity: string;
}

interface PhonologicalAnalysisData {
  items: PhonologicalProcess[];
  summary: string;
  age_appropriate: boolean;
  recommended_focus: string[];
}

interface TherapyGoal {
  icf_code: string;
  goal_text: string;
  methods: string[];
  milestones: string[];
  timeframe: string;
}

interface TherapyPhaseData {
  phase_name: string;
  goals: TherapyGoal[];
  duration: string;
}

interface TherapyPlanData {
  patient_pseudonym: string;
  diagnose_text: string;
  plan_phases: TherapyPhaseData[];
  frequency: string;
  total_sessions: number;
  elternberatung: string;
  haeusliche_uebungen: string[];
}

interface ComparisonItem {
  category: string;
  initial_finding: string;
  current_finding: string;
  change: string;
  details: string;
}

interface ReportComparisonData {
  items: ComparisonItem[];
  overall_progress: string;
  remaining_issues: string[];
  recommendation: string;
}

/* ═══════════════════════════════ Main Component ═════════════════════════════ */

export default function Home() {
  const [activeModule, setActiveModule] = useState<AppModule>("report");
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
  const [savedReportId, setSavedReportId] = useState<number | null>(null);
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
        setMessages((prev) => prev.slice(0, -1)); // rollback user message
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
      if ((data as { _db_id?: number })._db_id) {
        setSavedReportId((data as { _db_id: number })._db_id);
      }
      setPhase("preview");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unbekannter Fehler.");
      setPhase("upload");
    }
  }

  // ── Render ─────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Header */}
      <header className="border-b border-border print:hidden">
        <div className="max-w-5xl mx-auto px-6">
          {/* Top bar: breadcrumb + controls */}
          <div className="flex items-center justify-between h-12">
            <div className="flex items-center gap-2 text-sm">
              <span className="font-extrabold tracking-tight text-foreground">
                Logopädie
              </span>
              <span className="text-border-strong font-light">/</span>
              <span className="font-semibold" style={{ color: "var(--accent-text)" }}>
                {({
                  report: "Berichterstellung",
                  phonology: "Ausspracheanalyse",
                  "therapy-plan": "Therapieplan",
                  compare: "Berichtsvergleich",
                  suggest: "Textbausteine",
                } as Record<AppModule, string>)[activeModule]}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <kbd className="hidden sm:inline-flex items-center gap-1 px-1.5 py-0.5 rounded border border-border-strong text-[10px] text-muted-foreground font-mono">
                ⌘K
              </kbd>
              <ThemeToggle />
            </div>
          </div>

          {/* Phase pills — report module only */}
          {activeModule === "report" && (
            <div className="flex items-center gap-2 pb-2 text-xs">
              {(
                [
                  { label: "① Anamnese", active: phase === "chat", done: phase !== "chat" },
                  { label: "② Material", active: phase === "upload", done: phase === "generating" || phase === "preview" },
                  { label: "③ Bericht", active: phase === "generating" || phase === "preview", done: false },
                ] as { label: string; active: boolean; done: boolean }[]
              ).map((step, i) => (
                <span key={i} className="flex items-center gap-2">
                  {i > 0 && <span className="text-muted-foreground">→</span>}
                  <span
                    className={`px-3 py-1 rounded-full font-medium transition-colors ${
                      step.active
                        ? "text-white"
                        : step.done
                        ? ""
                        : "text-muted-foreground"
                    }`}
                    style={
                      step.active
                        ? { background: "var(--accent)", color: "white" }
                        : step.done
                        ? { background: "var(--accent-muted)", color: "var(--accent-text)" }
                        : { background: "var(--surface-elevated)" }
                    }
                  >
                    {step.label}
                  </span>
                </span>
              ))}
            </div>
          )}

          {/* Module tabs */}
          <nav className="flex gap-1 -mb-px overflow-x-auto">
            {([
              ["report", "Berichterstellung"],
              ["phonology", "Ausspracheanalyse"],
              ["therapy-plan", "Therapieplan"],
              ["compare", "Berichtsvergleich"],
              ["suggest", "Textbausteine"],
            ] as [AppModule, string][]).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setActiveModule(key)}
                className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  activeModule === key
                    ? "border-[var(--accent)] text-[var(--accent-text)]"
                    : "border-transparent text-muted-foreground hover:text-foreground hover:border-border-strong"
                }`}
              >
                {label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-8 flex flex-col gap-6">
        {/* Error — hidden on WelcomeScreen (shown inline there instead) */}
        {error && (
          <div
            role="alert"
            className="rounded-lg bg-error-surface border border-error-border px-5 py-4 text-sm text-error-text flex items-start gap-3 print:hidden"
          >
            <AlertIcon />
            <span>{error}</span>
          </div>
        )}

        {/* ── Module: Phonological Analysis ─────────────────────── */}
        {activeModule === "phonology" && (
          <PhonologicalAnalysisView api={API} />
        )}

        {/* ── Module: Therapy Plan ──────────────────────────────── */}
        {activeModule === "therapy-plan" && (
          <TherapyPlanView api={API} sessionId={sessionId} />
        )}

        {/* ── Module: Report Comparison ─────────────────────────── */}
        {activeModule === "compare" && (
          <ReportComparisonView api={API} />
        )}

        {/* ── Module: Text Suggestions ──────────────────────────── */}
        {activeModule === "suggest" && (
          <TextSuggestionView api={API} />
        )}

        {/* ── Module: Report (original phases) ──────────────────── */}
        {activeModule === "report" && phase === "chat" && (
          <>
            {currentPhase !== "greeting" && (
              <div className="flex items-center justify-between">
                <h1 className="text-xl font-semibold tracking-tight">
                  Anamnese-Gespräch
                </h1>
                {collectedFields.length > 0 && (
                  <span className="text-xs text-muted-foreground">
                    {collectedFields.length} Felder erfasst
                  </span>
                )}
              </div>
            )}

            {/* Chat messages */}
            <div className="flex-1 flex flex-col gap-3 overflow-y-auto max-h-[60vh] rounded-lg border border-border bg-surface p-4 card-elevated">
              {messages.map((msg, i) => (
                <ChatBubble key={i} role={msg.role} content={msg.content} />
              ))}
              {currentPhase === "greeting" && (
                <QuickReplyBubbles onSelect={sendMessage} disabled={isSending} />
              )}
              {isSending && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Spinner /> Antwort wird generiert…
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Input area — hidden during greeting phase */}
            {currentPhase !== "greeting" && (
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
                  className="flex-1 rounded-lg bg-input border border-border-strong px-4 py-3 text-sm text-foreground placeholder:text-muted focus:outline-none focus:border-ring disabled:opacity-40"
                />
                {!isRecording ? (
                  <button
                    onClick={startRecording}
                    disabled={isSending}
                    className="px-4 py-3 rounded-lg bg-surface-elevated hover:bg-border-strong text-foreground/80 transition-colors disabled:opacity-40"
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
                  className="px-6 py-3 rounded-lg bg-accent hover:bg-accent-hover text-white font-medium text-sm transition-colors disabled:opacity-40 btn-accent-glow"
                >
                  Senden
                </button>
              </div>
            )}

            {/* Transition to upload */}
            {isAnamnesisComplete && (
              <div className="flex items-center gap-3 rounded-lg border border-accent px-5 py-4 bg-accent-muted">
                <span className="text-sm text-accent-text">
                  Anamnese abgeschlossen! Sie können jetzt Materialien
                  hochladen oder direkt den Bericht generieren.
                </span>
                <button
                  onClick={() => setPhase("upload")}
                  className="shrink-0 px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors btn-accent-glow"
                >
                  Weiter
                </button>
              </div>
            )}
          </>
        )}

        {/* ── Phase: Upload ──────────────────────────────────────── */}
        {activeModule === "report" && phase === "upload" && (
          <>
            <div className="flex items-center justify-between">
              <h1 className="text-xl font-semibold tracking-tight">
                Materialien hochladen
              </h1>
              <button
                onClick={() => setPhase("chat")}
                className="text-sm text-muted-foreground hover:text-foreground"
              >
                ← Zurück zum Gespräch
              </button>
            </div>

            <p className="text-sm text-muted-foreground">
              Laden Sie vorhandene Berichte, Diagnostik-Ergebnisse oder
              Verordnungen hoch (PDF, DOCX, TXT). Diese werden als Kontext für
              die Berichterstellung verwendet. Dieser Schritt ist optional.
            </p>

            {/* Drop zone */}
            <DropZone onFiles={handleFileUpload} />

            {/* File list */}
            {uploadedFiles.length > 0 && (
              <div className="flex flex-col gap-2">
                <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-widest">
                  Hochgeladene Dateien
                </h2>
                {uploadedFiles.map((f, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-3 rounded-lg bg-surface border border-border px-4 py-3 text-sm"
                  >
                    <FileIcon />
                    <span className="text-foreground">{f.filename}</span>
                    <span className="text-xs text-muted ml-auto">
                      {f.extracted_text.length} Zeichen extrahiert
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Generate button */}
            <button
              onClick={generateReport}
              className="self-start px-6 py-3 rounded-lg bg-accent hover:bg-accent-hover text-white font-medium text-sm transition-colors btn-accent-glow"
            >
              Bericht generieren
            </button>
          </>
        )}

        {/* ── Phase: Generating ──────────────────────────────────── */}
        {activeModule === "report" && phase === "generating" && (
          <div className="flex-1 flex flex-col items-center justify-center gap-4">
            <Spinner />
            <p className="text-sm text-muted-foreground">
              Bericht wird generiert… Dies kann einen Moment dauern.
            </p>
          </div>
        )}

        {/* ── Phase: Preview ─────────────────────────────────────── */}
        {activeModule === "report" && phase === "preview" && report && (
          <>
            <div className="flex flex-col gap-2 print:hidden">
              <div className="flex items-center justify-between">
                <h1 className="text-xl font-semibold tracking-tight">
                  Generierter Bericht
                </h1>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPhase("upload")}
                    className="text-sm text-muted-foreground hover:text-foreground"
                  >
                    ← Zurück
                  </button>
                  <button
                    onClick={() => window.print()}
                    className="px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors"
                  >
                    Drucken / PDF
                  </button>
                </div>
              </div>
              <div className="flex gap-4">
                {savedReportId && (
                  <Link
                    href={`/berichte/${savedReportId}`}
                    className="text-sm text-muted-foreground hover:underline"
                  >
                    Bericht dauerhaft ansehen →
                  </Link>
                )}
                <Link
                  href="/berichte"
                  className="text-sm text-muted-foreground hover:underline"
                >
                  Alle Berichte
                </Link>
              </div>
            </div>
            <ReportPreview report={report} />
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-border px-6 py-4 text-center text-xs text-muted print:hidden">
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
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "text-white rounded-br-md"
            : "bg-surface-elevated text-foreground rounded-bl-md"
        }`}
        style={isUser ? { background: "var(--accent)" } : undefined}
      >
        {isUser ? (
          content
        ) : (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h1: ({ children }) => (
                <h1 className="text-base font-bold text-accent mb-2 mt-1">{children}</h1>
              ),
              h2: ({ children }) => (
                <h2 className="text-sm font-bold text-accent mb-1.5 mt-1">{children}</h2>
              ),
              h3: ({ children }) => (
                <h3 className="text-sm font-semibold text-foreground/90 mb-1 mt-1">{children}</h3>
              ),
              p: ({ children }) => (
                <p className="mb-2 last:mb-0">{children}</p>
              ),
              ul: ({ children }) => (
                <ul className="list-disc list-inside mb-2 space-y-0.5 pl-1">{children}</ul>
              ),
              ol: ({ children }) => (
                <ol className="list-decimal list-inside mb-2 space-y-0.5 pl-1">{children}</ol>
              ),
              li: ({ children }) => (
                <li className="text-foreground/90">{children}</li>
              ),
              strong: ({ children }) => (
                <strong className="font-semibold text-foreground">{children}</strong>
              ),
              em: ({ children }) => (
                <em className="italic text-foreground/80">{children}</em>
              ),
              code: ({ children }) => (
                <code className="bg-black/10 dark:bg-white/10 rounded px-1 py-0.5 text-xs font-mono">{children}</code>
              ),
              hr: () => (
                <hr className="my-2 border-border/50" />
              ),
            }}
          >
            {content}
          </ReactMarkdown>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════ Quick-Reply Bubbles ════════════════════════════ */

const QUICK_REPLY_TYPES = [
  'Befundbericht',
  'Therapiebericht kurz',
  'Therapiebericht lang',
  'Abschlussbericht',
  '✏️ Sonstiges...',
] as const;

function QuickReplyBubbles({
  onSelect,
  disabled,
}: {
  onSelect: (type: string) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex flex-wrap gap-2 pl-10 pt-1">
      {QUICK_REPLY_TYPES.map((t) => {
        const isOther = t.startsWith('✏️');
        return (
          <button
            key={t}
            onClick={() => onSelect(t)}
            disabled={disabled}
            className={[
              'rounded-full border px-4 py-2 text-sm transition-all duration-150',
              'disabled:opacity-40 disabled:cursor-not-allowed',
              isOther
                ? 'border-border-strong text-muted-foreground hover:text-foreground hover:border-border-strong bg-surface'
                : 'border-accent/50 text-accent-text bg-accent-muted hover:bg-accent-muted/80',
            ].join(' ')}
          >
            {t}
          </button>
        );
      })}
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
          ? "border-accent bg-accent-muted"
          : "border-border-strong bg-surface/50 hover:bg-surface"
      }`}
    >
      <UploadIcon />
      <p className="text-sm text-muted-foreground">
        Dateien hierher ziehen oder <span className="text-accent-text">durchsuchen</span>
      </p>
      <p className="text-xs text-muted">PDF, DOCX oder TXT · Max. 10 MB</p>
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
    <div className="rounded-lg border border-border overflow-hidden divide-y divide-border print:border-black print:divide-black print:text-black print:bg-white">
      {/* Header */}
      <div className="px-6 py-4 bg-surface print:bg-white">
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
    <div className="px-6 py-4 bg-surface/60 print:bg-white">
      <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-2 print:text-black print:font-bold print:text-sm print:normal-case">
        {title}
      </h3>
      <div className="text-sm text-foreground leading-relaxed whitespace-pre-wrap print:text-black">
        {children}
      </div>
    </div>
  );
}

/* ═══════════════════════════ Phonological Analysis View ══════════════════════ */

function PhonologicalAnalysisView({ api }: { api: string }) {
  const [wordPairs, setWordPairs] = useState<{ target: string; production: string }[]>([
    { target: "", production: "" },
  ]);
  const [childAge, setChildAge] = useState("");
  const [result, setResult] = useState<PhonologicalAnalysisData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function addPair() {
    setWordPairs((prev) => [...prev, { target: "", production: "" }]);
  }

  function updatePair(index: number, field: "target" | "production", value: string) {
    setWordPairs((prev) => prev.map((p, i) => (i === index ? { ...p, [field]: value } : p)));
  }

  function removePair(index: number) {
    if (wordPairs.length > 1) setWordPairs((prev) => prev.filter((_, i) => i !== index));
  }

  async function analyze() {
    const valid = wordPairs.filter((p) => p.target.trim() && p.production.trim());
    if (!valid.length) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${api}/analysis/phonological-text?${childAge ? `child_age=${encodeURIComponent(childAge)}` : ""}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(valid),
      });
      if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail ?? "Analyse fehlgeschlagen.");
      setResult(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler.");
    } finally {
      setLoading(false);
    }
  }

  const severityColors: Record<string, string> = {
    leicht: "bg-yellow-900 text-yellow-300",
    mittel: "bg-orange-900 text-orange-300",
    schwer: "bg-red-900 text-red-300",
  };

  return (
    <>
      <h1 className="text-xl font-semibold tracking-tight">Phonologische Prozessanalyse</h1>
      <p className="text-sm text-muted-foreground">
        Geben Sie Zielwörter und die tatsächliche Produktion des Kindes ein. Die KI identifiziert
        automatisch phonologische Prozesse und bewertet den Schweregrad.
      </p>

      <div className="flex items-center gap-3">
        <label className="text-sm text-muted-foreground">Alter des Kindes:</label>
        <input
          type="text"
          value={childAge}
          onChange={(e) => setChildAge(e.target.value)}
          placeholder="z.B. 4;6 Jahre"
          className="rounded-lg bg-surface border border-border-strong px-3 py-2 text-sm w-40 focus:outline-none focus:border-ring"
        />
      </div>

      <div className="flex flex-col gap-2">
        {wordPairs.map((pair, i) => (
          <div key={i} className="flex items-center gap-2">
            <input
              type="text"
              value={pair.target}
              onChange={(e) => updatePair(i, "target", e.target.value)}
              placeholder="Zielwort"
              className="flex-1 rounded-lg bg-surface border border-border-strong px-3 py-2 text-sm focus:outline-none focus:border-ring"
            />
            <span className="text-muted">→</span>
            <input
              type="text"
              value={pair.production}
              onChange={(e) => updatePair(i, "production", e.target.value)}
              placeholder="Produktion"
              className="flex-1 rounded-lg bg-surface border border-border-strong px-3 py-2 text-sm focus:outline-none focus:border-ring"
            />
            <button onClick={() => removePair(i)} className="text-muted hover:text-red-400 text-sm px-2">✕</button>
          </div>
        ))}
        <button onClick={addPair} className="self-start text-sm text-accent-text hover:text-accent-text">+ Weiteres Wortpaar</button>
      </div>

      <button
        onClick={analyze}
        disabled={loading}
        className="self-start px-6 py-3 rounded-lg bg-accent hover:bg-accent-hover text-white font-medium text-sm transition-colors disabled:opacity-40"
      >
        {loading ? "Analysiere…" : "Analyse starten"}
      </button>

      {error && <div className="rounded-lg bg-red-950 border border-red-800 px-5 py-4 text-sm text-red-300">{error}</div>}

      {result && (
        <div className="flex flex-col gap-4">
          {/* Results table */}
          <div className="rounded-lg border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-surface text-muted-foreground text-xs uppercase tracking-wider">
                  <th className="px-4 py-3 text-left">Zielwort</th>
                  <th className="px-4 py-3 text-left">Produktion</th>
                  <th className="px-4 py-3 text-left">Prozesse</th>
                  <th className="px-4 py-3 text-left">Schwere</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {result.items.map((item, i) => (
                  <tr key={i} className="bg-surface/60">
                    <td className="px-4 py-3 font-mono">{item.target_word}</td>
                    <td className="px-4 py-3 font-mono text-red-300">{item.production}</td>
                    <td className="px-4 py-3">
                      <ul className="space-y-1">
                        {item.processes.map((p, j) => (
                          <li key={j} className="text-xs text-foreground/80">{p}</li>
                        ))}
                      </ul>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-1 rounded-full ${severityColors[item.severity] || "bg-surface-elevated text-muted-foreground"}`}>
                        {item.severity}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Summary */}
          <div className="rounded-lg border border-border bg-surface/60 px-5 py-4">
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-2">Zusammenfassung</h3>
            <p className="text-sm text-foreground whitespace-pre-wrap">{result.summary}</p>
            <div className="mt-3 flex items-center gap-2">
              <span className={`text-xs px-2 py-1 rounded-full ${result.age_appropriate ? "bg-green-900 text-green-300" : "bg-red-900 text-red-300"}`}>
                {result.age_appropriate ? "Altersgemäß" : "Nicht altersgemäß"}
              </span>
            </div>
            {result.recommended_focus.length > 0 && (
              <div className="mt-3">
                <h4 className="text-xs text-muted-foreground mb-1">Empfohlene Therapieschwerpunkte:</h4>
                <ul className="space-y-1">
                  {result.recommended_focus.map((f, i) => (
                    <li key={i} className="text-sm text-accent-text flex items-start gap-2">
                      <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-accent shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}

/* ═══════════════════════════ Therapy Plan View ═══════════════════════════════ */

function TherapyPlanView({ api, sessionId }: { api: string; sessionId: string | null }) {
  const [plan, setPlan] = useState<TherapyPlanData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generatePlan() {
    if (!sessionId) {
      setError("Bitte erstellen Sie zuerst einen Bericht im Tab 'Berichterstellung'.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${api}/sessions/${sessionId}/therapy-plan`, { method: "POST" });
      if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail ?? "Plan-Generierung fehlgeschlagen.");
      setPlan(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <h1 className="text-xl font-semibold tracking-tight">KI-gestützter Therapieplan</h1>
      <p className="text-sm text-muted-foreground">
        Generieren Sie einen strukturierten Therapieplan mit ICF-Bezug basierend auf dem
        erstellten Befundbericht. Führen Sie zuerst eine Anamnese im Tab
        &quot;Berichterstellung&quot; durch.
      </p>

      <button
        onClick={generatePlan}
        disabled={loading}
        className="self-start px-6 py-3 rounded-lg bg-accent hover:bg-accent-hover text-white font-medium text-sm transition-colors disabled:opacity-40"
      >
        {loading ? "Generiere Therapieplan…" : "Therapieplan generieren"}
      </button>

      {error && <div className="rounded-lg bg-red-950 border border-red-800 px-5 py-4 text-sm text-red-300">{error}</div>}

      {plan && (
        <div className="rounded-lg border border-border overflow-hidden divide-y divide-border print:border-black print:text-black print:bg-white">
          <div className="px-6 py-4 bg-surface print:bg-white">
            <h2 className="text-lg font-semibold">Therapieplan: {plan.patient_pseudonym}</h2>
            <p className="text-sm text-muted-foreground mt-1">{plan.diagnose_text}</p>
            <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
              <span>Frequenz: {plan.frequency}</span>
              <span>Gesamt: {plan.total_sessions} Sitzungen</span>
            </div>
          </div>

          {plan.plan_phases.map((phase, pi) => (
            <div key={pi} className="px-6 py-4 bg-surface/60">
              <h3 className="text-sm font-semibold text-accent-text mb-3">
                Phase {pi + 1}: {phase.phase_name}
                <span className="text-xs text-muted-foreground font-normal ml-2">{phase.duration}</span>
              </h3>
              <div className="space-y-4">
                {phase.goals.map((goal, gi) => (
                  <div key={gi} className="rounded-lg bg-surface-elevated/50 p-4">
                    <div className="flex items-start gap-2 mb-2">
                      <span className="text-xs px-2 py-0.5 rounded bg-accent-muted text-accent-text shrink-0 font-mono">
                        {goal.icf_code}
                      </span>
                      <span className="text-sm text-foreground">{goal.goal_text}</span>
                    </div>
                    <div className="ml-4 space-y-2 text-xs">
                      <div>
                        <span className="text-muted-foreground">Methoden: </span>
                        <span className="text-foreground/80">{goal.methods.join(", ")}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Meilensteine: </span>
                        <span className="text-foreground/80">{goal.milestones.join(" → ")}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Zeitrahmen: </span>
                        <span className="text-foreground/80">{goal.timeframe}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}

          {plan.elternberatung && (
            <div className="px-6 py-4 bg-surface/60">
              <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-2">Elternberatung</h3>
              <p className="text-sm text-foreground whitespace-pre-wrap">{plan.elternberatung}</p>
            </div>
          )}

          {plan.haeusliche_uebungen.length > 0 && (
            <div className="px-6 py-4 bg-surface/60">
              <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-2">Häusliche Übungen</h3>
              <ul className="space-y-1">
                {plan.haeusliche_uebungen.map((u, i) => (
                  <li key={i} className="text-sm text-foreground flex items-start gap-2">
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-accent shrink-0" />
                    {u}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="px-6 py-3 bg-surface flex justify-end print:hidden">
            <button
              onClick={() => window.print()}
              className="px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors"
            >
              Drucken / PDF
            </button>
          </div>
        </div>
      )}
    </>
  );
}

/* ═══════════════════════════ Report Comparison View ══════════════════════════ */

function ReportComparisonView({ api }: { api: string }) {
  const [result, setResult] = useState<ReportComparisonData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const initialRef = useRef<HTMLInputElement>(null);
  const currentRef = useRef<HTMLInputElement>(null);

  async function compare() {
    const initialFile = initialRef.current?.files?.[0];
    const currentFile = currentRef.current?.files?.[0];
    if (!initialFile || !currentFile) {
      setError("Bitte wählen Sie beide Berichte aus.");
      return;
    }
    setLoading(true);
    setError(null);
    const formData = new FormData();
    formData.append("initial_report", initialFile);
    formData.append("current_report", currentFile);
    try {
      const res = await fetch(`${api}/analysis/compare`, { method: "POST", body: formData });
      if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail ?? "Vergleich fehlgeschlagen.");
      setResult(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler.");
    } finally {
      setLoading(false);
    }
  }

  const changeColors: Record<string, string> = {
    verbessert: "bg-green-900 text-green-300",
    "unverändert": "bg-surface-elevated text-muted-foreground",
    verschlechtert: "bg-red-900 text-red-300",
  };

  return (
    <>
      <h1 className="text-xl font-semibold tracking-tight">Vergleichende Berichtsanalyse</h1>
      <p className="text-sm text-muted-foreground">
        Laden Sie zwei Berichte hoch (z.B. Erstbefund und aktueller Befund). Die KI analysiert
        Veränderungen und erstellt einen strukturierten Fortschrittsbericht.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="flex flex-col gap-2">
          <label className="text-sm text-muted-foreground">Erstbefund / Älterer Bericht:</label>
          <input ref={initialRef} type="file" accept=".pdf,.docx,.txt" className="text-sm text-muted-foreground file:mr-3 file:rounded-lg file:border-0 file:bg-surface-elevated file:px-4 file:py-2 file:text-sm file:text-foreground/80 file:cursor-pointer" />
        </div>
        <div className="flex flex-col gap-2">
          <label className="text-sm text-muted-foreground">Aktueller Bericht:</label>
          <input ref={currentRef} type="file" accept=".pdf,.docx,.txt" className="text-sm text-muted-foreground file:mr-3 file:rounded-lg file:border-0 file:bg-surface-elevated file:px-4 file:py-2 file:text-sm file:text-foreground/80 file:cursor-pointer" />
        </div>
      </div>

      <button
        onClick={compare}
        disabled={loading}
        className="self-start px-6 py-3 rounded-lg bg-accent hover:bg-accent-hover text-white font-medium text-sm transition-colors disabled:opacity-40"
      >
        {loading ? "Vergleiche…" : "Berichte vergleichen"}
      </button>

      {error && <div className="rounded-lg bg-red-950 border border-red-800 px-5 py-4 text-sm text-red-300">{error}</div>}

      {result && (
        <div className="flex flex-col gap-4">
          {/* Comparison table */}
          <div className="rounded-lg border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-surface text-muted-foreground text-xs uppercase tracking-wider">
                  <th className="px-4 py-3 text-left">Bereich</th>
                  <th className="px-4 py-3 text-left">Erstbefund</th>
                  <th className="px-4 py-3 text-left">Aktuell</th>
                  <th className="px-4 py-3 text-left">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {result.items.map((item, i) => (
                  <tr key={i} className="bg-surface/60">
                    <td className="px-4 py-3 font-medium text-foreground/80">{item.category}</td>
                    <td className="px-4 py-3 text-muted-foreground text-xs">{item.initial_finding}</td>
                    <td className="px-4 py-3 text-foreground/80 text-xs">{item.current_finding}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-1 rounded-full ${changeColors[item.change] || "bg-surface-elevated text-muted-foreground"}`}>
                        {item.change}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Summary */}
          <div className="rounded-lg border border-border bg-surface/60 px-5 py-4 space-y-3">
            <div>
              <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-1">Gesamtfortschritt</h3>
              <p className="text-sm text-foreground whitespace-pre-wrap">{result.overall_progress}</p>
            </div>
            {result.remaining_issues.length > 0 && (
              <div>
                <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-1">Verbleibende Probleme</h3>
                <ul className="space-y-1">{result.remaining_issues.map((r, i) => (
                  <li key={i} className="text-sm text-orange-300 flex items-start gap-2">
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-orange-500 shrink-0" />{r}
                  </li>
                ))}</ul>
              </div>
            )}
            <div>
              <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-1">Empfehlung</h3>
              <p className="text-sm text-foreground whitespace-pre-wrap">{result.recommendation}</p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/* ═══════════════════════════ Text Suggestion View ════════════════════════════ */

function TextSuggestionView({ api }: { api: string }) {
  const [text, setText] = useState("");
  const [reportType, setReportType] = useState("befundbericht");
  const [disorder, setDisorder] = useState("");
  const [section, setSection] = useState("befund");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function onTextChange(val: string) {
    setText(val);
    if (timerRef.current) clearTimeout(timerRef.current);
    if (val.trim().length > 10) {
      timerRef.current = setTimeout(() => fetchSuggestions(val), 800);
    } else {
      setSuggestions([]);
    }
  }

  async function fetchSuggestions(input: string) {
    setLoading(true);
    try {
      const res = await fetch(`${api}/suggest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: input, report_type: reportType, disorder, section }),
      });
      if (!res.ok) return;
      const data = await res.json();
      setSuggestions(data.suggestions || []);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }

  function applySuggestion(s: string) {
    setText(text + s);
    setSuggestions([]);
  }

  return (
    <>
      <h1 className="text-xl font-semibold tracking-tight">Intelligente Textbausteine</h1>
      <p className="text-sm text-muted-foreground">
        Beginnen Sie einen Satz und die KI schlägt kontextbezogene Vervollständigungen
        mit logopädischer Fachsprache vor. Klicken Sie auf einen Vorschlag zum Übernehmen.
      </p>

      {/* Context selectors */}
      <div className="flex flex-wrap gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground">Berichtstyp</label>
          <select value={reportType} onChange={(e) => setReportType(e.target.value)}
            className="rounded-lg bg-surface border border-border-strong px-3 py-2 text-sm focus:outline-none focus:border-ring">
            <option value="befundbericht">Befundbericht</option>
            <option value="therapiebericht_kurz">Therapiebericht (kurz)</option>
            <option value="therapiebericht_lang">Therapiebericht (lang)</option>
            <option value="abschlussbericht">Abschlussbericht</option>
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground">Abschnitt</label>
          <select value={section} onChange={(e) => setSection(e.target.value)}
            className="rounded-lg bg-surface border border-border-strong px-3 py-2 text-sm focus:outline-none focus:border-ring">
            <option value="anamnese">Anamnese</option>
            <option value="befund">Befund</option>
            <option value="therapieindikation">Therapieindikation</option>
            <option value="therapieverlauf">Therapieverlauf</option>
            <option value="empfehlung">Empfehlung</option>
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground">Störungsbild</label>
          <input type="text" value={disorder} onChange={(e) => setDisorder(e.target.value)}
            placeholder="z.B. SP1, ST2"
            className="rounded-lg bg-surface border border-border-strong px-3 py-2 text-sm w-32 focus:outline-none focus:border-ring" />
        </div>
      </div>

      {/* Text editor */}
      <div className="relative">
        <textarea
          value={text}
          onChange={(e) => onTextChange(e.target.value)}
          rows={8}
          placeholder="Beginnen Sie hier zu schreiben, z.B. 'Die phonologische Bewertung ergab...'"
          className="w-full rounded-lg bg-surface border border-border-strong px-4 py-3 text-sm leading-relaxed resize-y focus:outline-none focus:border-ring"
        />
        {loading && (
          <div className="absolute top-3 right-3">
            <Spinner />
          </div>
        )}
      </div>

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-widest">
            Vorschläge (klicken zum Übernehmen)
          </h3>
          {suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => applySuggestion(s)}
              className="text-left rounded-lg bg-surface border border-border hover:border-accent px-4 py-3 text-sm text-foreground/80 transition-colors"
            >
              <span className="text-muted">{text}</span>
              <span className="text-accent-text">{s}</span>
            </button>
          ))}
        </div>
      )}
    </>
  );
}

/* ═══════════════════════════════ Icons / Spinner ═════════════════════════════ */

function ChevronRight() {
  return (
    <svg className="w-3 h-3 text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
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
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-muted-foreground">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" />
    </svg>
  );
}

function FileIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4 text-muted-foreground">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
    </svg>
  );
}

function Spinner() {
  return (
    <svg className="w-4 h-4 motion-safe:animate-spin text-accent-text shrink-0" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4Z" />
    </svg>
  );
}
