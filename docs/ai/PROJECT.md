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
| State management | React Context (AuthProvider, SessionProvider) | Zustand not used |
| Backend / API | FastAPI (Python) | REST, runs on port 8001 |
| AI — STT | Groq Whisper large-v3 | Audio transcription |
| AI — NLP | Groq Llama-3.3-70b | Report generation, chat, analysis |
| Session storage | Upstash Redis | Fernet-encrypted, 24h TTL; also rate-limit backend |
| Database | Neon PostgreSQL via SQLModel | Users, reports, patients, audit log |
| Auth | JWT (access + refresh, httpOnly cookies) + TOTP-2FA + email verification + audit log | Multi-user; admin role for `/admin/*` |
| BFF | Next route handlers (`src/app/auth-api/*`, `src/app/backend-api/[...path]/*`) | Browser never talks to backend directly |
| Hosting | Vercel Services (experimentalServices) | Monorepo via vercel.json (backend `routePrefix: /api`) |
| CI/CD | GitHub Actions | 7 parallel jobs: backend lint/typecheck/test, frontend lint/test/build, Playwright E2E |

---

## Package Manager & Tooling

| Tool | Command | Notes |
|---|---|---|
| Dev server (both) | `./dev.sh` | Starts backend :8001 + frontend :3000 |
| Frontend tests | `cd frontend && npm test` | Vitest + Testing Library |
| Backend tests | `cd backend && python -m pytest` | ~270 test functions across ~60 files |
| E2E tests | `cd frontend && npx playwright test` | 32 cases / 11 specs, Chromium-only in CI |
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
│   ├── routers/             — 13 APIRouter modules
│   │                          (auth, auth_admin, health, sessions, patients,
│   │                           reports, analysis, therapy_plans, suggestions,
│   │                           exports, soap, legacy)
│   ├── middleware/          — auth.py (JWT bearer), rate_limiter.py (slowapi+Redis)
│   ├── models/              — Pydantic v2 schemas + SQLModel tables
│   ├── services/            — Business logic (~22 service modules incl.
│   │                          auth_service, audit_service, totp_service,
│   │                          token_service, patient_service, encryption_service,
│   │                          anamnesis_engine, report_generator, ...)
│   └── tests/               — pytest
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── (auth)/                    — login, register, verify-email,
│   │   │   │                                 forgot-password, reset-password
│   │   │   ├── admin/audit/               — Admin-only audit log view
│   │   │   ├── auth-api/                  — BFF: /auth-api/* → backend /auth/*
│   │   │   ├── backend-api/[...path]/     — BFF proxy: /backend-api/* → backend
│   │   │   ├── berichte/[id]/             — Report deeplink view
│   │   │   ├── module/[slug]/             — Module pages (report, phonology, soap, …)
│   │   │   ├── patienten/{,neu,[id]}      — Patient list / create / detail
│   │   │   ├── settings/security/         — 2FA setup, password change
│   │   │   └── proxy.ts                   — Middleware: auth gating + role check
│   │   ├── features/        — auth, chat, report, phonology, therapy-plan,
│   │   │                      compare, suggest, history, soap, patients,
│   │   │                      patient-progress
│   │   ├── components/      — AppShell, ErrorBoundary, ErrorAlert, MobileSidebar,
│   │   │                      OnboardingOverlay, ResetConfirmDialog, ThemeToggle, …
│   │   ├── hooks/           — useAudioRecording, …
│   │   ├── providers/       — AuthProvider, SessionProvider, ThemeProvider
│   │   ├── types/           — Centralized TypeScript types
│   │   └── lib/api.ts       — API client (default base: "/backend-api")
│   ├── e2e/                 — Playwright specs (chromium only in CI)
│   └── vitest.config.ts
├── docs/ai/                 — AI workflow state files (this directory)
├── scripts/                 — AI session helper scripts
├── .github/workflows/ci.yml — 7 parallel CI jobs
└── vercel.json              — Vercel Services config (backend routePrefix /api)
```

---

## Architecture Notes

- **Monorepo**: independent frontend (Next.js) + backend (FastAPI) deployed via Vercel Services.
- **Port convention**: Backend always `:8001`, frontend `:3000`. Only `dev.sh` is authoritative — `frontend/next.config.ts` is empty (no rewrites). The frontend client fetches `/backend-api` by default; override only via `NEXT_PUBLIC_API_URL`, which is **baked into the production bundle at build time** (setting an absolute host breaks Playwright `/backend-api`-pattern mocks).
- **BFF (Backend-for-Frontend)**: the browser never talks to the backend directly. Two Next route-handler trees mediate every call:
  - `src/app/auth-api/*` — auth endpoints, sets/clears httpOnly cookies.
  - `src/app/backend-api/[...path]/route.ts` — generic proxy; attaches `Authorization: Bearer <access_token>` from cookie.
- **Auth model**: JWT access + refresh tokens in httpOnly cookies, plus a non-httpOnly `user_role` cookie for UI gating (backend still enforces auth on every request). TOTP-2FA, mandatory email verification, password-reset flow, session list, lockout, admin audit log.
- **Middleware** (`frontend/src/proxy.ts`): redirects unauthenticated requests to `/login`, gates `/admin/*` to role `admin`, allows demo mode on `/module/report` + `/module/soap`.
- **Persistence**: Session state in Upstash Redis (Fernet-encrypted, 24h TTL). Users, reports, patients, audit log persist to Neon PostgreSQL via SQLModel.
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

Authoritative source: `backend/.env.example`. Frequently-used names:

```text
# Core
GROQ_API_KEY
ALLOWED_ORIGINS
DATABASE_URL

# Redis (sessions + rate limit)
KV_REST_API_URL
KV_REST_API_TOKEN

# Auth / JWT
JWT_SECRET
JWT_ACCESS_TTL_SECONDS
JWT_REFRESH_TTL_SECONDS

# Email (verification + password reset)
SMTP_*  (host/port/user/password/from)

# Encryption-at-rest
FERNET_KEY
```

Frontend honors `NEXT_PUBLIC_API_URL` (override the default `/backend-api` base — see Architecture Notes for caveats).

---

## External Dependencies & Integrations

| Service | Purpose | Notes |
| --- | --- | --- |
| Groq API | Whisper STT + Llama NLP | Central AI engine |
| Upstash Redis | Session state + rate limit | Fernet-encrypted, 24h TTL |
| Neon PostgreSQL | Persistent storage (users, reports, patients, audit) | Via SQLModel |
| SMTP provider | Email verification + password reset | Configured via SMTP_* env vars |
| Vercel | Hosting | experimentalServices (beta) |
| GitHub Actions | CI | 7 parallel jobs |

---

## Known Constraints & Fragile Areas

- Max upload: 25 MB audio, 10 MB material, max 5 materials per session.
- Session IDs: 12-char hex strings — validated via regex in all layers.
- Rate limiting via slowapi + Redis — tests pin the limiter in-memory.
- `NEXT_PUBLIC_API_URL` is baked into the production bundle; do NOT set an absolute host in the E2E CI job (breaks `/backend-api/*` Playwright mocks).
- Vercel `experimentalServices` is beta and may change without notice.
- E2E tests require `npx playwright install chromium`.
- `actions/checkout@v4` + `actions/setup-node@v4` use Node 20 — GitHub will force Node 24 on **2026-06-02**; bump action versions before then.

---

## Last Updated

- Date: 2026-05-28
- Updated by: Claude Code (M-4 docs sync)
- Reason: Sync stale facts after auth/patients/admin/BFF rollouts — added auth model, BFF architecture, updated router/service/CI counts, corrected port-convention note, expanded env-var list.
