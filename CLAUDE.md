# Logopädie Report Agent – Claude Context

@AGENTS.md

## Was dieses Projekt ist

AI-gestütztes Tool für Logopäden: Aufnahme von Therapiesitzungen → automatische strukturierte Berichte via Groq.
Portfolio-Projekt (Demo/Showcase), deployed auf Vercel als Monorepo mit Vercel Services.

## Stack

| Schicht | Tech |
|---|---|
| Frontend | Next.js 16, React 19, Tailwind CSS v4, TypeScript |
| Backend | FastAPI, Python 3.12, Pydantic v2, SQLModel |
| AI | Groq API — Whisper large-v3 (STT) + Llama-3.3-70b (NLP) |
| Auth | JWT (access + refresh, httpOnly Cookies), TOTP-2FA, Email-Verifizierung, Audit-Log |
| Persistence | Upstash Redis (Sessions + Rate Limit, Fernet-encrypted), Neon PostgreSQL (User, Reports, Patients) |
| Deploy | Vercel Services (`vercel.json` → `experimentalServices`) |
| CI | GitHub Actions (lint, typecheck, test — backend + frontend, plus Playwright E2E) |

## Struktur

```
/
├── backend/
│   ├── main.py              # FastAPI App + exception handlers
│   ├── database.py          # SQLModel engine + get_db dependency
│   ├── dependencies.py      # Singleton service instances (groq, store, ...)
│   ├── exceptions.py        # Custom exception hierarchy
│   ├── logging_config.py    # Structured logging setup
│   ├── routers/             # 13 APIRouter-Module
│   │   ├── auth.py          # /auth/* — Login, 2FA, Passwort, Email, Sessions
│   │   ├── auth_admin.py    # /admin/* — Audit-Log, User-Lock, 2FA-Disable
│   │   ├── health.py        # GET /health (+ public /livez)
│   │   ├── sessions.py      # Session CRUD + chat/audio/upload/generate
│   │   ├── patients.py      # /patients/* — CRUD + history/progress/consents
│   │   ├── reports.py       # GET /reports, /reports/{id}, /reports/stats
│   │   ├── analysis.py      # Phonological analysis + compare
│   │   ├── therapy_plans.py # POST /sessions/{id}/therapy-plan
│   │   ├── suggestions.py   # POST /suggest
│   │   ├── exports.py       # GET /reports/{id}/pdf
│   │   ├── soap.py          # POST /sessions/{id}/soap, GET /reports/{id}/soap
│   │   └── legacy.py        # POST /process-audio (deprecated)
│   ├── middleware/
│   │   ├── auth.py          # JWT-Bearer extraction + user resolution
│   │   └── rate_limiter.py  # Redis-backed slowapi rate limiting
│   ├── models/              # Pydantic v2 schemas + SQLModel tables
│   ├── services/            # Business logic (22 service modules, u.a. auth_service,
│   │                        #   audit_service, totp_service, token_service,
│   │                        #   patient_service, encryption_service,
│   │                        #   anamnesis_engine, report_generator, ...)
│   └── tests/               # pytest
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── (auth)/                     # login, register, verify-email,
│   │   │   │                                #   forgot-password, reset-password
│   │   │   ├── admin/audit/                # Admin-only Audit-Log-View
│   │   │   ├── auth-api/                   # BFF: /auth-api/* → backend /auth/*
│   │   │   ├── backend-api/[...path]/      # BFF-Proxy: /backend-api/* → backend
│   │   │   ├── berichte/[id]/              # Bericht-Deeplink-View
│   │   │   ├── module/[slug]/              # Module: report, phonology, soap, ...
│   │   │   ├── patienten/{,neu,[id]}       # Patient-Liste + Create + Detail
│   │   │   ├── settings/security/          # 2FA-Setup, Passwort ändern
│   │   │   └── proxy.ts                    # Middleware: Auth-Gating + Role-Check
│   │   ├── features/        # auth, chat, report, phonology, therapy-plan, compare,
│   │   │                    #   suggest, history, soap, patients, patient-progress
│   │   ├── components/      # AppShell, ErrorBoundary, ErrorAlert, MobileSidebar,
│   │   │                    #   OnboardingOverlay, ResetConfirmDialog, ThemeToggle, ...
│   │   ├── hooks/           # Custom hooks (useAudioRecording, ...)
│   │   ├── providers/       # AuthProvider, SessionProvider, ThemeProvider
│   │   ├── types/           # Centralized TypeScript types
│   │   └── lib/api.ts       # API-Client (Default-Base: "/backend-api")
│   ├── e2e/                 # Playwright Specs (chromium-only in CI)
│   └── vitest.config.ts     # Vitest + Testing Library
├── .github/workflows/ci.yml # 7 parallel Jobs (Backend Lint/Test/Type, Frontend Lint/Test/Build/E2E)
├── .pre-commit-config.yaml  # ruff + standard hooks
└── vercel.json              # experimentalServices: backend (routePrefix /api) + frontend
```

## API-Endpunkte (FastAPI)

Backend-Pfade so wie der FastAPI-Router sie definiert. In Production (Vercel) liegt
der Backend-Service unter `/api/*` (siehe `vercel.json`); in Development direkt auf
`:8001`. Das Frontend ruft das Backend **nie** direkt, sondern über zwei BFF-Route-Handler:

- `frontend/src/app/auth-api/*` — bündelt Auth-Calls, setzt/löscht Session-Cookies
- `frontend/src/app/backend-api/[...path]/route.ts` — Allgemeiner Proxy, hängt
  `Authorization: Bearer <access_token>` aus dem httpOnly-Cookie an

### Auth (`/auth/*`)

- `POST /auth/register` · `POST /auth/verify-email` · `POST /auth/resend-verification`
- `POST /auth/login` · `POST /auth/login/2fa` · `POST /auth/refresh` · `POST /auth/logout`
- `GET  /auth/me`
- `POST /auth/password/reset/request` · `POST /auth/password/reset/confirm` · `POST /auth/password/change`
- `POST /auth/2fa/setup` · `POST /auth/2fa/enable` · `POST /auth/2fa/disable`
- `GET  /auth/sessions` · `DELETE /auth/sessions/{session_id}`

### Admin (`/admin/*`, Rolle `admin`)

- `GET  /admin/audit`
- `POST /admin/users/{user_id}/lock` · `POST /admin/users/{user_id}/unlock` · `POST /admin/users/{user_id}/disable-2fa`

### Patients (`/patients/*`)

- `POST /patients` · `GET /patients` · `GET/PATCH/DELETE /patients/{id}`
- `GET  /patients/{id}/history` · `GET /patients/{id}/progress`
- `GET  /patients/{id}/consents` · `POST /patients/{id}/consent`

### Sessions / Anamnese

- `POST /sessions` · `GET /sessions/{id}`
- `POST /sessions/{id}/chat` · `POST /sessions/{id}/audio` · `POST /sessions/{id}/upload`
- `POST /sessions/{id}/generate` · `GET /sessions/{id}/report`
- `POST /sessions/{id}/therapy-plan` · `POST /sessions/{id}/soap`

### Reports / SOAP / Export

- `GET  /reports` · `GET /reports/stats` · `GET /reports/{id}`
- `GET  /reports/{id}/pdf` · `GET /reports/{id}/soap`

### Analyse / Vorschläge

- `POST /analysis/phonological` · `POST /analysis/phonological-text` · `POST /analysis/compare`
- `POST /suggest`

### Health

- `GET /health` · `GET /livez` (unauthenticated probe)

## Report-Typen

`befundbericht` | `therapiebericht_kurz` | `therapiebericht_lang` | `abschlussbericht`

## Lokale Entwicklung

```bash
# Beide Services parallel (empfohlen)
./dev.sh

# Oder einzeln:
cd backend && pip install -r requirements.txt -r requirements-dev.txt
uvicorn backend.main:app --reload --port 8001

cd frontend && npm install && npm run dev

# Tests
cd backend && python -m pytest
cd frontend && npm test
cd frontend && npx playwright test      # E2E (chromium)
```

> **Port-Konvention:** Backend läuft IMMER auf `:8001`, Frontend auf `:3000`.
> Der Frontend-Client fetcht standardmäßig gegen `/backend-api` (BFF-Proxy in
> `src/app/backend-api/[...path]/route.ts`), nicht direkt gegen das Backend.
> Überschreibbar via `NEXT_PUBLIC_API_URL` — aber Achtung: das Env wird **bei
> `npm run build` ins Bundle eingebacken**, und ein absoluter Host bricht die
> Playwright-Mocks, die auf `/backend-api/*` matchen. Für die E2E-Job-Defaults
> siehe Kommentar in `.github/workflows/ci.yml` (Section `frontend-e2e`).

Env-Vars (Auswahl): `GROQ_API_KEY`, `ALLOWED_ORIGINS`, `KV_REST_API_URL`,
`KV_REST_API_TOKEN`, `DATABASE_URL`, JWT/Email/2FA-Secrets (siehe `backend/.env.example`).

## Deploy

```bash
vercel deploy
```

## Wichtige Hinweise

- **Auth:** JWT in httpOnly-Cookies (`access_token` + `refresh_token`); UI-Rolle
  zusätzlich in nicht-httpOnly `user_role` (Backend prüft Autorisierung trotzdem
  Server-seitig auf jedem Request). 2FA via TOTP, Email-Verifizierung Pflicht.
- **BFF-Architektur:** Browser → Next-Route-Handler (`/auth-api/*`, `/backend-api/*`) →
  Backend. Direktverkehr zum Backend gibt es im Frontend nicht.
- **Middleware:** `frontend/src/proxy.ts` gated alle Nicht-Auth-/Nicht-API-Pfade
  auf `access_token`-Cookie und prüft `admin`-Rolle für `/admin/*`.
- **Persistenz:**
  - Session-State in **Upstash Redis** (Fernet-encrypted, 24h TTL)
  - User, Reports, Patients persistent in **Neon PostgreSQL** via SQLModel
- **Audit-Log:** `audit_service` schreibt sicherheitsrelevante Events; Admin-UI
  unter `/admin/audit`.
- **Limits:** Max Upload 25 MB (Audio), 10 MB (Material), max 5 Materialien pro Session.
- **Session-IDs:** 12-Zeichen Hex-Strings (validated via regex).
- **Rate Limiting:** slowapi + Redis (Tests pinnen den Limiter in-memory).
- **`sys.path.insert(0, backend/)`** in main.py → Imports ohne `backend.`-Prefix
  (Tests müssen denselben Pfad nutzen).
- **Linting:** ruff (backend), ESLint (frontend); Type-Check: mypy (backend), tsc (frontend).
- **E2E-Specs** mocken den BFF-Pfad via `page.route("**/backend-api/**")` bzw.
  `**/auth-api/**` — wer den Default-API-Base ändert, muss die Mocks mitziehen.
