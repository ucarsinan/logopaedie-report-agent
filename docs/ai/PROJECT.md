# PROJECT.md — Permanent Project Context

> This file describes stable, long-lived project facts.
> Update it when the stack, architecture, or conventions change.
> Do NOT use it for current working state — use `CURRENT.md` for that.

---

## Project Overview

**Name:** Logopädie Report Agent
**Purpose:** AI-powered tool for speech therapists — records therapy sessions and generates structured reports automatically via Groq (Whisper STT + Llama NLP).
**Status:** Portfolio / Demo (deployed on Vercel, not a production product)
**Primary users:** Speech therapists (Logopäden); showcases AI integration skills
**Repository:** private

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Language | TypeScript 5.x / Python 3.12 | Monorepo: frontend + backend |
| Framework (frontend) | Next.js 16, React 19 | App Router, Server Components by default |
| Styling | Tailwind CSS v4 | No CSS Modules |
| State management | React Context (SessionProvider) | Zustand not used |
| Backend / API | FastAPI (Python) | REST, runs on port 8001 |
| AI — STT | Groq Whisper large-v3 | Audio transcription |
| AI — NLP | Groq Llama-3.3-70b | Report generation, chat, analysis |
| Session storage | Upstash Redis | Fernet-encrypted, 24h TTL |
| Database | Neon PostgreSQL via SQLModel | Persistent reports |
| Auth | Optional API-key middleware | Not enforced in demo mode |
| Hosting | Vercel Services (experimentalServices) | Monorepo via vercel.json |
| CI/CD | GitHub Actions | 6 parallel jobs: lint, typecheck, pytest, vitest, e2e |

---

## Package Manager & Tooling

| Tool | Command | Notes |
|---|---|---|
| Dev server (both) | `./dev.sh` | Starts backend :8001 + frontend :3000 |
| Frontend tests | `cd frontend && npm test` | Vitest + Testing Library |
| Backend tests | `cd backend && python -m pytest` | 35 tests |
| E2E tests | `cd frontend && npx playwright test` | 32 Chromium tests |
| Type check (frontend) | `cd frontend && npx tsc --noEmit` | |
| Type check (backend) | `cd backend && mypy .` | |
| Lint (frontend) | `cd frontend && npm run lint` | ESLint |
| Lint (backend) | `cd backend && ruff check .` | via pre-commit |
| Deploy | `vercel deploy` | |

---

## Repository Structure

```
/
├── backend/
│   ├── main.py              — FastAPI app + exception handlers
│   ├── database.py          — SQLModel engine + get_db dependency
│   ├── dependencies.py      — Singleton service instances
│   ├── exceptions.py        — Custom exception hierarchy
│   ├── routers/             — 9 APIRouter modules (health, sessions, reports, analysis, ...)
│   ├── middleware/          — auth.py, rate_limiter.py
│   ├── models/              — Pydantic v2 schemas + SQLModel tables
│   ├── services/            — Business logic (11 service modules)
│   └── tests/               — pytest (35 tests)
├── frontend/
│   ├── src/
│   │   ├── app/             — Next.js App Router pages
│   │   ├── features/        — chat, report, phonology, therapy-plan, compare, suggest, history, soap
│   │   ├── components/      — Shared: ErrorBoundary, ErrorAlert, Suspense wrappers
│   │   ├── hooks/           — useAudioRecording
│   │   ├── providers/       — SessionProvider, ThemeProvider
│   │   ├── types/           — Centralized TypeScript types
│   │   └── lib/api.ts       — API client (20+ endpoints)
│   └── vitest.config.ts
├── docs/ai/                 — AI workflow state files (this directory)
├── scripts/                 — AI session helper scripts
├── .github/workflows/ci.yml — 6 parallel CI jobs
└── vercel.json              — Vercel Services config
```

---

## Architecture Notes

- **Monorepo**: independent frontend (Next.js) + backend (FastAPI) deployed via Vercel Services.
- **Port convention**: Backend always `:8001`, frontend `:3000`. Must stay in sync across: `dev.sh`, `frontend/next.config.ts`, `frontend/src/lib/api.ts`.
- **Session state** in Upstash Redis (Fernet-encrypted, 24h TTL). Reports persist to Neon PostgreSQL.
- **`sys.path.insert(0, backend/)` in `main.py`** — imports work without `backend.` prefix; tests must replicate this.
- **Server Components** by default; `use client` only when required.
- **Feature modules** in `frontend/src/features/` — each feature is self-contained.

---

## Coding Conventions

- Commits: Conventional Commits format, English only.
- Error handling: typed return values, explicit catch — no silent catch.
- No `any` in TypeScript. No hardcoded secrets. Never log sensitive values.
- File naming: `kebab-case.ts` for files, `PascalCase` for React components.

---

## Report Types

`befundbericht` | `therapiebericht_kurz` | `therapiebericht_lang` | `abschlussbericht`

---

## Environment Variables (names only)

```text
GROQ_API_KEY
ALLOWED_ORIGINS
KV_REST_API_URL
KV_REST_API_TOKEN
DATABASE_URL
```

---

## External Dependencies & Integrations

| Service | Purpose | Notes |
| --- | --- | --- |
| Groq API | Whisper STT + Llama NLP | Central AI engine |
| Upstash Redis | Session state (encrypted) | 24h TTL |
| Neon PostgreSQL | Persistent report storage | Via SQLModel |
| Vercel | Hosting | experimentalServices (beta) |
| GitHub Actions | CI | 6 parallel jobs |

---

## Known Constraints & Fragile Areas

- Max upload: 25 MB audio, 10 MB material, max 5 materials per session.
- Session IDs: 12-char hex strings — validated via regex in all layers.
- Rate limiting via slowapi + Redis — mock carefully in tests.
- Vercel `experimentalServices` is beta and may change without notice.
- E2E tests require `npx playwright install chromium`.

---

## Last Updated

- Date: 2026-05-10
- Updated by: Claude Code
- Reason: Initial fill-in after ai-dev-workflow-template installation
