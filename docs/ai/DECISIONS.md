# DECISIONS.md — Architecture & Workflow Decisions

> This file documents significant decisions about architecture, tooling, and workflow.
> Record a decision here when it affects project structure, is non-obvious, or involves a meaningful tradeoff.
> Do NOT document minor implementation details.

---

## ADR-P1: KI-Architektur für logopaedie-praxis (Echtes Produkt)

**Date:** 2026-05-10
**Status:** Accepted
**Decided by:** human
**Scope:** Gilt ausschließlich für `logopaedie-praxis` — NICHT für `logopaedie-report-agent`

**Context:**
`logopaedie-praxis` ist ein echtes Medizinprodukt das Patientendaten (Audio-Aufnahmen, Diagnosen, Therapiedokumentation) verarbeitet. Patientendaten unterliegen in Deutschland §203 StGB (ärztliche/therapeutische Schweigepflicht) und DSGVO. Der DSGVO-konforme Transfer von Patientendaten an US-basierte KI-APIs (Groq, OpenAI US, Anthropic) ist ohne explizite Einwilligung jedes Patienten und ohne valide SCCs (Standardvertragsklauseln) nicht zulässig. Im Streitfall haftet die Praxis strafrechtlich.

### Entscheidung: Abstrahierte KI-Provider-Schicht mit lokalem KI als Default

```text
AIProvider Interface
  transcribe(audio) -> text
  generate(prompt)  -> text

LocalProvider (Default)       | CloudProvider (EU only, optional)
------------------------------|----------------------------------
STT: faster-whisper (lokal)   | STT: faster-whisper auf EU-Server
NLP: Ollama + Llama (lokal)   | NLP: Mistral AI (Paris, EU-DPA)
                              |      ODER Azure OpenAI (West EU)
                              | Anonymisierungs-Layer PFLICHT:
                              | Kein Patientenname in Prompts!
```

### Explizit VERBOTEN für logopaedie-praxis

- Groq API (keine EU-Region, kein klares DSGVO-DPA)
- OpenAI direkt (US, kein EU-Data-Residency im Basis-Tarif)
- Anthropic Claude API (keine EU-Region)
- Jede US-API die rohe Patientenaudio oder ungeschwärzten Therapietext empfängt

### Lokale KI — Technischer Stack

- STT: `faster-whisper` (Python, läuft auf CPU/GPU, Whisper-Modell lokal)
- NLP: `Ollama` mit `llama3.2:3b` (CPU, ausreichend für Reports) oder `llama3.3:70b` (GPU)
- Minimale Hardware: 8 GB RAM, kein GPU nötig für Basis-Qualität
- Empfohlene Hardware: 16 GB RAM + Nvidia GPU für Llama 70B

### EU-Cloud als Alternative (für Praxen ohne eigene Hardware)

- Provider: Mistral AI (Frankreich, EU-DSGVO-konform, API-Key-Modell)
- Anonymisierungs-Regel: Prompt enthält NIEMALS Name, Geburtsdatum, Adresse, Versichertennummer
- Prompt enthält NUR medizinischen/therapeutischen Inhalt und Session-interne Pseudonym-ID

**Rationale:**
Echte Praxissoftware muss ohne rechtliches Risiko betreibbar sein. Eine abstrahierte Provider-Schicht kostet ~1 Woche Mehraufwand, spart aber potenzielle Strafverfolgung und verhindert komplette Architektur-Rewrites wenn der erste Provider gewechselt werden muss.

**Konsequenzen:**

- `logopaedie-praxis/backend/services/ai_provider.py` definiert das Provider-Interface
- `LocalProvider` ist der Default in `config.py`
- `CloudProvider` (Mistral) ist optional konfigurierbar per Env-Var `AI_PROVIDER=cloud`
- Der Implementierungsplan (IMPLEMENTATION_PLAN_B1.md) Task 14 muss entsprechend umgeschrieben werden

**Alternativen abgewogen:**

- Weiter Groq: rechtlich nicht vertretbar für Produktion
- Nur EU-Cloud (Mistral): kein lokaler Fallback, Abhängigkeit von externem Service
- Nur lokal: kein Angebot für Praxen ohne Hardware — schränkt Zielgruppe ein

---

## ADR-000: Shared AI Repository State

**Date:** 2026-05-10
**Status:** Accepted
**Decided by:** human

**Context:** Multiple AI agents (Claude Code, Codex, Gemini) may work on this codebase across different sessions with no shared memory.

**Decision:** Use versioned repository files (`docs/ai/`) as the single source of truth for AI session state. All agents must read and update these files at session boundaries.

**Rationale:** Chat histories are not portable, are lost on context window exhaustion, and cannot be reviewed by humans. Repository files are durable, version-controlled, and accessible by any agent or tool.

**Consequences:** Every meaningful session must end with updated `CURRENT.md`, `TASKS.md`, and `HANDOFF.md`. Small overhead, high continuity benefit.

**Alternatives considered:** Relying on chat history (not portable, not persistent across tools); external database (adds infrastructure complexity with no benefit for a single-developer project).

---

## ADR-001: Groq for AI Processing (STT + NLP)

**Date:** 2026-05-10
**Status:** Accepted
**Decided by:** human + Claude Code

**Context:** The project needs fast, affordable speech-to-text (Whisper) and large language model inference (report generation, chat). Options evaluated: OpenAI API, Groq, local models.

**Decision:** Use Groq API for both STT (Whisper large-v3) and NLP (Llama-3.3-70b).

**Rationale:** Groq offers the fastest inference speed for Whisper and Llama models among cloud providers at the time of decision. Speed is critical for interactive therapy session recording. Cost is low enough for a portfolio demo.

**Consequences:** Single external AI dependency (Groq API key required). If Groq has downtime, the entire AI pipeline is unavailable. Model versions are fixed — must update manually when newer models are available.

**Alternatives considered:** OpenAI (higher cost, slightly slower for STT); local models (too slow on typical developer hardware for Whisper large-v3).

---

## ADR-002: Upstash Redis for Session State

**Date:** 2026-05-10
**Status:** Accepted
**Decided by:** human + Claude Code

**Context:** Therapy sessions require persistent state across multiple HTTP requests (anamnesis chat, audio uploads, report generation). This state is ephemeral — it does not need to survive beyond 24 hours.

**Decision:** Use Upstash Redis with Fernet encryption for session state. 24-hour TTL per session.

**Rationale:** Upstash Redis is serverless-compatible (works on Vercel without connection pooling issues), has a generous free tier, and supports TTL natively. Fernet encryption protects patient-related session content at rest.

**Consequences:** Sessions expire after 24 hours by design. Session IDs must be 12-char hex strings (validated via regex in all layers). Do not store decrypted session content in logs.

**Alternatives considered:** In-memory state (not viable on serverless); Neon PostgreSQL for sessions (heavier, no native TTL, overkill for ephemeral state).

---

## ADR-003: Neon PostgreSQL for Report Persistence

**Date:** 2026-05-10
**Status:** Accepted
**Decided by:** human + Claude Code

**Context:** Generated reports must survive beyond the session TTL and be retrievable by report ID or patient.

**Decision:** Use Neon PostgreSQL (serverless Postgres) with SQLModel ORM for persistent report storage.

**Rationale:** Neon is serverless-compatible, has a free tier, and Postgres is well-understood. SQLModel integrates well with FastAPI and Pydantic v2.

**Consequences:** Reports are persistent and queryable. Schema changes require migrations (SQLModel auto-migration in dev; handle carefully in production). `DATABASE_URL` must be set in all environments.

**Alternatives considered:** SQLite (not suitable for serverless multi-instance deployments); Supabase (more features than needed, adds complexity not required for this project).

---

## ADR-004: Vercel experimentalServices for Monorepo Deployment

**Date:** 2026-05-10
**Status:** Accepted
**Decided by:** human

**Context:** The project is a monorepo with a Next.js frontend and a FastAPI backend. Both need to deploy together without a separate backend hosting service.

**Decision:** Use Vercel's `experimentalServices` feature in `vercel.json` to deploy both from the same repository.

**Rationale:** Simplifies deployment to a single `vercel deploy` command. Keeps the project on the free/hobby tier.

**Consequences:** `experimentalServices` is beta — Vercel may change or remove it without notice. Backend runs as a Vercel function — cold starts possible. Port 8001 convention applies locally only; Vercel proxies via `/api/*` rewrites.

**Alternatives considered:** Separate backend on Fly.io or Railway (more stable, but adds deployment complexity and cost); Next.js API routes only (would require rewriting the entire Python backend).

---

## ADR-005: Feature Module Structure for Frontend

**Date:** 2026-05-10
**Status:** Accepted
**Decided by:** Claude Code

**Context:** The frontend has many distinct functional areas: chat, report, phonology, therapy-plan, soap, history, compare, suggest. A flat components directory would become unmanageable.

**Decision:** Organize frontend code into self-contained feature modules under `frontend/src/features/`.

**Rationale:** Scales better than a flat structure. Each feature can be understood in isolation. Reduces cross-feature coupling.

**Consequences:** New features get their own directory under `features/`. Shared UI lives in `components/`, shared types in `types/`. Do not import from one feature directory into another — use shared layers instead.

**Alternatives considered:** Flat `components/` directory (works for small apps, does not scale).
