"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { REPORT_TYPE_LABELS } from "@/types";
import type { ChatMsg, ReportSummary, TherapyPlanSummary } from "@/types";
import type { TherapyPlanData } from "@/types/therapy-plan";
import { WorkflowStepper } from "@/components/WorkflowStepper";
import type { StepConfig } from "@/components/WorkflowStepper";

type TpMode = "select" | "chat" | "from-report" | "generating" | "plan";

const THERAPY_PLAN_STEPS: StepConfig[] = [
  {
    label: "Eingabe",
    infoTitle: "Patienten auswählen oder Daten eingeben",
    infoText:
      "Starten Sie einen Mini-Chat für einen neuen Patienten oder wählen Sie einen gespeicherten Bericht als Grundlage.",
  },
  {
    label: "Generieren",
    infoTitle: "Therapieplan wird generiert",
    infoText: "Der KI-Assistent erstellt jetzt einen ICF-basierten Therapieplan. Dies dauert wenige Sekunden.",
  },
  {
    label: "Plan",
    infoTitle: "Therapieplan fertig",
    infoText:
      "Prüfen und bearbeiten Sie den Therapieplan. Klicken Sie auf \u2713 Eingabe um neu zu starten.",
    infoVariant: "success" as const,
  },
];

interface TherapyPlanModuleProps {
  sessionId: string | null;
}

export function TherapyPlanModule({ sessionId: _sessionId }: TherapyPlanModuleProps) {
  const [tpMode, setTpMode] = useState<TpMode>("select");
  const [tpSessionId, setTpSessionId] = useState<string | null>(null);
  const [tpReportId, setTpReportId] = useState<number | null>(null);
  const [tpMessages, setTpMessages] = useState<ChatMsg[]>([]);
  const [tpInput, setTpInput] = useState("");
  const [tpIsSending, setTpIsSending] = useState(false);
  const [tpIsComplete, setTpIsComplete] = useState(false);
  const [plan, setPlan] = useState<TherapyPlanData | null>(null);
  const [tpSavedId, setTpSavedId] = useState<number | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState<TherapyPlanData | null>(null);
  const [savedPlans, setSavedPlans] = useState<TherapyPlanSummary[]>([]);
  const [savedReports, setSavedReports] = useState<ReportSummary[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const tpChatEndRef = useRef<HTMLDivElement>(null);

  const stepIndex = tpMode === "select" || tpMode === "chat" || tpMode === "from-report" ? 0
    : tpMode === "generating" ? 1
    : 2;

  useEffect(() => {
    api.therapyPlans.list().then(setSavedPlans).catch(() => {});
    api.reports.list().then((res) => setSavedReports(res.items)).catch(() => {});
  }, []);

  useEffect(() => {
    tpChatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [tpMessages]);

  async function startMiniChat() {
    setError(null);
    try {
      const data = await api.sessions.create("therapy_plan");
      setTpSessionId(data.session_id);
      const greeting = data.collected_data?.greeting ?? "Guten Tag! Für welchen Patienten möchten Sie einen Therapieplan erstellen?";
      setTpMessages([{ role: "assistant", content: greeting }]);
      setTpMode("chat");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler.");
    }
  }

  async function sendTpMessage() {
    if (!tpInput.trim() || !tpSessionId || tpIsSending) return;
    const msg = tpInput.trim();
    setTpInput("");
    setTpMessages((prev) => [...prev, { role: "user", content: msg }]);
    setTpIsSending(true);
    setError(null);
    try {
      const data = await api.sessions.chat(tpSessionId, msg);
      setTpMessages((prev) => [...prev, { role: "assistant", content: data.message }]);
      if (data.is_anamnesis_complete) setTpIsComplete(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler.");
    } finally {
      setTpIsSending(false);
    }
  }

  async function generateFromSession(sid: string, rid?: number) {
    setTpMode("generating");
    setError(null);
    try {
      const p = await api.sessions.therapyPlan(sid);
      setPlan(p);
      if (rid) setTpReportId(rid);
      setTpMode("plan");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler.");
      setTpMode(tpSessionId ? "chat" : "from-report");
    }
  }

  async function generateFromReport() {
    const rid = parseInt(selectedReportId);
    if (!rid) return;
    setError(null);
    try {
      const sessionData = await api.sessions.create("anamnesis");
      const sid = sessionData.session_id;
      setTpSessionId(sid);
      await generateFromSession(sid, rid);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler.");
    }
  }

  async function savePlan() {
    if (!plan || !tpSessionId) return;
    setIsSaving(true);
    setError(null);
    try {
      const saved = await api.therapyPlans.save(
        tpSessionId,
        plan as unknown as Record<string, unknown>,
        tpReportId ?? undefined,
      );
      setTpSavedId(saved.id);
      setSavedPlans((prev) => [saved, ...prev]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler.");
    } finally {
      setIsSaving(false);
    }
  }

  async function saveEditedPlan() {
    if (!editData || !tpSavedId) return;
    setIsSaving(true);
    setError(null);
    try {
      await api.therapyPlans.update(
        tpSavedId,
        editData as unknown as Record<string, unknown>,
      );
      setPlan(editData);
      setIsEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler.");
    } finally {
      setIsSaving(false);
    }
  }

  async function loadSavedPlan(id: number) {
    setError(null);
    try {
      const data = await api.therapyPlans.get(id);
      setPlan(data as unknown as TherapyPlanData);
      setTpSavedId((data._db_id as number | undefined) ?? id);
      setTpMode("plan");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler.");
    }
  }

  function resetToSelect() {
    setTpMode("select");
    setTpSessionId(null);
    setTpReportId(null);
    setTpMessages([]);
    setTpIsComplete(false);
    setPlan(null);
    setTpSavedId(null);
    setIsEditing(false);
    setEditData(null);
    setError(null);
    setSelectedReportId("");
  }

  return (
    <>
      <WorkflowStepper
        steps={THERAPY_PLAN_STEPS}
        currentStep={stepIndex}
        onStepClick={stepIndex > 0 ? (i) => { if (i === 0) resetToSelect(); } : undefined}
      />

      <h1 className="text-xl font-semibold tracking-tight">KI-gestützter Therapieplan</h1>

      {error && (
        <div className="rounded-lg bg-red-950 border border-red-800 px-5 py-4 text-sm text-red-300">{error}</div>
      )}

      {/* Select mode */}
      {tpMode === "select" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <button
              onClick={startMiniChat}
              className="flex flex-col gap-2 rounded-lg border border-border bg-surface px-5 py-4 text-left hover:border-accent transition-colors"
            >
              <span className="text-sm font-semibold text-foreground">Neu (Mini-Chat)</span>
              <span className="text-xs text-muted-foreground">
                Kurzes Gespräch (4 Fragen) für einen neuen Patienten — ohne vorherige Anamnese.
              </span>
            </button>
            <button
              onClick={() => setTpMode("from-report")}
              className="flex flex-col gap-2 rounded-lg border border-border bg-surface px-5 py-4 text-left hover:border-accent transition-colors"
            >
              <span className="text-sm font-semibold text-foreground">Aus Bericht</span>
              <span className="text-xs text-muted-foreground">
                Therapieplan auf Basis eines bereits gespeicherten Berichts erstellen.
              </span>
            </button>
          </div>

          {savedPlans.length > 0 && (
            <div>
              <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-2">
                Gespeicherte Therapiepläne
              </h2>
              <div className="rounded-lg border border-border divide-y divide-border overflow-hidden">
                {savedPlans.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => loadSavedPlan(p.id)}
                    className="w-full flex items-center justify-between px-4 py-3 bg-surface hover:bg-surface-elevated text-left transition-colors"
                  >
                    <div>
                      <p className="text-sm font-medium text-foreground">{p.patient_pseudonym}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(p.created_at).toLocaleDateString("de-DE")}
                        {p.report_id ? ` \u00b7 Bericht #${p.report_id}` : ""}
                      </p>
                    </div>
                    <span className="text-xs text-accent">Laden {"\u2192"}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Mini-chat mode */}
      {tpMode === "chat" && (
        <div className="space-y-4">
          <div className="rounded-lg border border-border bg-surface min-h-[200px] max-h-[380px] overflow-y-auto p-4 space-y-3">
            {tpMessages.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`rounded-lg px-4 py-2 text-sm max-w-[80%] whitespace-pre-wrap ${
                    m.role === "user"
                      ? "bg-accent text-white"
                      : "bg-surface-elevated text-foreground"
                  }`}
                >
                  {m.content}
                </div>
              </div>
            ))}
            {tpIsSending && (
              <div className="flex justify-start">
                <div className="rounded-lg px-4 py-2 text-sm bg-surface-elevated text-muted-foreground">…</div>
              </div>
            )}
            <div ref={tpChatEndRef} />
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              value={tpInput}
              onChange={(e) => setTpInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendTpMessage()}
              placeholder="Ihre Antwort…"
              disabled={tpIsSending}
              className="flex-1 rounded-lg border border-border bg-surface px-4 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-accent disabled:opacity-40"
            />
            <button
              onClick={sendTpMessage}
              disabled={tpIsSending || !tpInput.trim()}
              className="px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors disabled:opacity-40"
            >
              Senden
            </button>
          </div>
          {tpIsComplete && (
            <button
              onClick={() => tpSessionId && generateFromSession(tpSessionId)}
              className="self-start px-6 py-3 rounded-lg bg-accent hover:bg-accent-hover text-white font-medium text-sm transition-colors"
            >
              Therapieplan generieren
            </button>
          )}
        </div>
      )}

      {/* From-report mode */}
      {tpMode === "from-report" && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Wählen Sie einen gespeicherten Bericht als Grundlage für den Therapieplan.
          </p>
          {savedReports.length === 0 ? (
            <p className="text-sm text-muted-foreground italic">Keine gespeicherten Berichte gefunden.</p>
          ) : (
            <div className="flex gap-3 items-center">
              <select
                value={selectedReportId}
                onChange={(e) => setSelectedReportId(e.target.value)}
                className="flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
              >
                <option value="">{"\u2014"} Bericht auswählen {"\u2014"}</option>
                {savedReports.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.pseudonym} {"\u00b7"} {REPORT_TYPE_LABELS[r.report_type] ?? r.report_type} {"\u00b7"}{" "}
                    {new Date(r.created_at).toLocaleDateString("de-DE")}
                  </option>
                ))}
              </select>
              <button
                onClick={generateFromReport}
                disabled={!selectedReportId}
                className="px-5 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors disabled:opacity-40"
              >
                Generieren
              </button>
            </div>
          )}
          <button
            onClick={() => setTpMode("select")}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            {"\u2190"} Zurück
          </button>
        </div>
      )}

      {/* Generating mode */}
      {tpMode === "generating" && (
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <div className="w-4 h-4 rounded-full border-2 border-accent border-t-transparent animate-spin" />
          Therapieplan wird generiert…
        </div>
      )}

      {/* Plan mode */}
      {tpMode === "plan" && plan && (
        <div className="space-y-4">
          <div className="rounded-lg border border-border overflow-hidden divide-y divide-border print:border-black print:text-black print:bg-white">
            {/* Header */}
            <div className="px-6 py-4 bg-surface print:bg-white">
              {isEditing ? (
                <div className="space-y-2">
                  <input
                    value={editData?.patient_pseudonym ?? ""}
                    onChange={(e) => setEditData((d) => d ? { ...d, patient_pseudonym: e.target.value } : d)}
                    className="w-full rounded border border-border bg-surface-elevated px-3 py-1.5 text-sm font-semibold text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
                    placeholder="Patient (Pseudonym)"
                  />
                  <textarea
                    value={editData?.diagnose_text ?? ""}
                    onChange={(e) => setEditData((d) => d ? { ...d, diagnose_text: e.target.value } : d)}
                    rows={2}
                    className="w-full rounded border border-border bg-surface-elevated px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-accent resize-none"
                    placeholder="Diagnose"
                  />
                  <div className="flex gap-3">
                    <input
                      value={editData?.frequency ?? ""}
                      onChange={(e) => setEditData((d) => d ? { ...d, frequency: e.target.value } : d)}
                      className="flex-1 rounded border border-border bg-surface-elevated px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
                      placeholder="Frequenz"
                    />
                    <input
                      type="number"
                      value={editData?.total_sessions ?? 0}
                      onChange={(e) => setEditData((d) => d ? { ...d, total_sessions: parseInt(e.target.value) || 0 } : d)}
                      className="w-28 rounded border border-border bg-surface-elevated px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
                      placeholder="Sitzungen"
                    />
                  </div>
                </div>
              ) : (
                <>
                  <h2 className="text-lg font-semibold">Therapieplan: {plan.patient_pseudonym}</h2>
                  <p className="text-sm text-muted-foreground mt-1">{plan.diagnose_text}</p>
                  <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                    <span>Frequenz: {plan.frequency}</span>
                    <span>Gesamt: {plan.total_sessions} Sitzungen</span>
                  </div>
                </>
              )}
            </div>

            {/* Phases */}
            {(isEditing ? editData?.plan_phases : plan.plan_phases)?.map((phase, pi) => (
              <div key={pi} className="px-6 py-4 bg-surface/60">
                <h3 className="text-sm font-semibold text-accent-text mb-3">
                  {isEditing ? (
                    <input
                      value={phase.phase_name}
                      onChange={(e) => setEditData((d) => {
                        if (!d) return d;
                        const phases = [...d.plan_phases];
                        phases[pi] = { ...phases[pi], phase_name: e.target.value };
                        return { ...d, plan_phases: phases };
                      })}
                      className="rounded border border-border bg-surface-elevated px-2 py-0.5 text-sm font-semibold text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
                    />
                  ) : (
                    <>Phase {pi + 1}: {phase.phase_name}</>
                  )}
                  <span className="text-xs text-muted-foreground font-normal ml-2">{phase.duration}</span>
                </h3>
                <div className="space-y-4">
                  {phase.goals.map((goal, gi) => (
                    <div key={gi} className="rounded-lg bg-surface-elevated/50 p-4">
                      <div className="flex items-start gap-2 mb-2">
                        <span className="text-xs px-2 py-0.5 rounded bg-accent-muted text-accent-text shrink-0 font-mono">
                          {goal.icf_code}
                        </span>
                        {isEditing ? (
                          <textarea
                            value={goal.goal_text}
                            onChange={(e) => setEditData((d) => {
                              if (!d) return d;
                              const phases = [...d.plan_phases];
                              const goals = [...phases[pi].goals];
                              goals[gi] = { ...goals[gi], goal_text: e.target.value };
                              phases[pi] = { ...phases[pi], goals };
                              return { ...d, plan_phases: phases };
                            })}
                            rows={2}
                            className="flex-1 rounded border border-border bg-surface-elevated px-2 py-1 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-accent resize-none"
                          />
                        ) : (
                          <span className="text-sm text-foreground">{goal.goal_text}</span>
                        )}
                      </div>
                      <div className="ml-4 space-y-2 text-xs">
                        <div>
                          <span className="text-muted-foreground">Methoden: </span>
                          {isEditing ? (
                            <input
                              value={goal.methods.join(", ")}
                              onChange={(e) => setEditData((d) => {
                                if (!d) return d;
                                const phases = [...d.plan_phases];
                                const goals = [...phases[pi].goals];
                                goals[gi] = { ...goals[gi], methods: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) };
                                phases[pi] = { ...phases[pi], goals };
                                return { ...d, plan_phases: phases };
                              })}
                              className="rounded border border-border bg-surface-elevated px-2 py-0.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-accent w-full mt-0.5"
                              placeholder="Methode 1, Methode 2, …"
                            />
                          ) : (
                            <span className="text-foreground/80">{goal.methods.join(", ")}</span>
                          )}
                        </div>
                        <div>
                          <span className="text-muted-foreground">Meilensteine: </span>
                          <span className="text-foreground/80">{goal.milestones.join(" \u2192 ")}</span>
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

            {/* Elternberatung */}
            {(isEditing ? editData?.elternberatung : plan.elternberatung) && (
              <div className="px-6 py-4 bg-surface/60">
                <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-2">Elternberatung</h3>
                {isEditing ? (
                  <textarea
                    value={editData?.elternberatung ?? ""}
                    onChange={(e) => setEditData((d) => d ? { ...d, elternberatung: e.target.value } : d)}
                    rows={3}
                    className="w-full rounded border border-border bg-surface-elevated px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-accent resize-none"
                  />
                ) : (
                  <p className="text-sm text-foreground whitespace-pre-wrap">{plan.elternberatung}</p>
                )}
              </div>
            )}

            {/* Häusliche Übungen */}
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

            {/* Action bar */}
            <div className="px-6 py-3 bg-surface flex items-center justify-between gap-3 print:hidden flex-wrap">
              <div className="flex gap-2">
                {isEditing ? (
                  <>
                    <button
                      onClick={saveEditedPlan}
                      disabled={isSaving || !tpSavedId}
                      className="px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors disabled:opacity-40"
                    >
                      {isSaving ? "Speichert…" : "Speichern"}
                    </button>
                    <button
                      onClick={() => { setIsEditing(false); setEditData(null); }}
                      className="px-4 py-2 rounded-lg border border-border text-sm text-muted-foreground hover:text-foreground transition-colors"
                    >
                      Abbrechen
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => { setIsEditing(true); setEditData(JSON.parse(JSON.stringify(plan))); }}
                    className="px-4 py-2 rounded-lg border border-border text-sm text-foreground hover:border-accent transition-colors"
                  >
                    Editieren
                  </button>
                )}
              </div>
              <div className="flex gap-2">
                {!tpSavedId && (
                  <button
                    onClick={savePlan}
                    disabled={isSaving}
                    className="px-4 py-2 rounded-lg border border-accent text-accent text-sm font-medium hover:bg-accent hover:text-white transition-colors disabled:opacity-40"
                  >
                    {isSaving ? "Speichert…" : "In Datenbank speichern"}
                  </button>
                )}
                {tpSavedId && (
                  <span className="text-xs text-muted-foreground self-center">{"\u2713"} Gespeichert</span>
                )}
                <button
                  onClick={() => window.print()}
                  className="px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors"
                >
                  Drucken / PDF
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
