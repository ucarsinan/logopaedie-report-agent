# Logopädie Report Agent – Claude Context

## Was dieses Projekt ist

AI-gestütztes Tool für Logopäden: Aufnahme von Therapiesitzungen → automatische strukturierte Berichte via Groq.
Portfolio-Projekt (Demo/Showcase), deployed auf Vercel als Monorepo mit Vercel Services.

## Stack

| Schicht | Tech |
|---|---|
| Frontend | Next.js 16, React 19, Tailwind CSS v4, TypeScript |
| Backend | FastAPI, Python 3.12, Pydantic v2, SQLModel |
| AI | Groq API — Whisper large-v3 (STT) + Llama-3.3-70b (NLP) |
| Persistence | Upstash Redis (Sessions, Fernet-encrypted), Neon PostgreSQL (Reports) |
| Deploy | Vercel Services (`vercel.json` → `experimentalServices`) |
| CI | GitHub Actions (lint, typecheck, test — backend + frontend) |

## Struktur

```
/
├── backend/
│   ├── main.py              # FastAPI App + exception handlers (~170 Zeilen)
│   ├── database.py          # SQLModel engine + get_db dependency
│   ├── dependencies.py      # Singleton service instances (groq, store, ...)
│   ├── exceptions.py        # Custom exception hierarchy
│   ├── logging_config.py    # Structured logging setup
│   ├── routers/             # 9 APIRouter-Module
│   │   ├── health.py        # GET /health
│   │   ├── sessions.py      # Session CRUD + chat/audio/upload/generate
│   │   ├── reports.py       # GET /reports, GET /reports/{id}
│   │   ├── analysis.py      # Phonological analysis + compare
│   │   ├── therapy_plans.py # POST /sessions/{id}/therapy-plan
│   │   ├── suggestions.py   # POST /suggest
│   │   ├── exports.py       # GET /reports/{id}/pdf
│   │   ├── soap.py          # POST /sessions/{id}/soap, GET /reports/{id}/soap
│   │   └── legacy.py        # POST /process-audio (deprecated)
│   ├── middleware/
│   │   ├── auth.py          # Optional API-Key auth
│   │   └── rate_limiter.py  # Redis-backed slowapi rate limiting
│   ├── models/              # Pydantic v2 schemas + SQLModel tables
│   ├── services/            # Business logic (11 service modules)
│   └── tests/               # pytest (35 tests)
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js App Router
│   │   ├── features/        # Feature modules (chat, report, phonology, ...)
│   │   ├── components/      # Shared components (ErrorBoundary, ErrorAlert, ...)
│   │   ├── hooks/           # Custom hooks (useAudioRecording)
│   │   ├── providers/       # SessionProvider, ThemeProvider
│   │   ├── types/           # Centralized TypeScript types
│   │   └── lib/api.ts       # API client wrapper (20+ endpoints)
│   └── vitest.config.ts     # Vitest + Testing Library
├── .github/workflows/ci.yml # 6 parallel CI jobs
├── .pre-commit-config.yaml  # ruff + standard hooks
└── vercel.json              # Services-Konfiguration
```

## API-Endpunkte (backend, routePrefix: /api)

- `GET  /health`
- `POST /sessions`                          → Session erstellen + Begrüßung
- `GET  /sessions/{id}`                     → Session-State lesen
- `POST /sessions/{id}/chat`                → Text-Chat (Anamnese)
- `POST /sessions/{id}/audio`               → Audio-Chat (Whisper → Chat)
- `POST /sessions/{id}/upload`              → Material-Upload (PDF, DOCX, TXT)
- `POST /sessions/{id}/generate`            → Bericht generieren (→ DB speichern)
- `GET  /sessions/{id}/report`              → Generierten Bericht abrufen
- `POST /sessions/{id}/therapy-plan`        → Therapieplan generieren
- `POST /sessions/{id}/soap`                → SOAP-Notes generieren
- `GET  /reports`                           → Report-Liste (paginiert)
- `GET  /reports/{id}`                      → Einzelner Report
- `GET  /reports/{id}/pdf`                  → PDF-Export
- `GET  /reports/{id}/soap`                 → SOAP-Notes abrufen
- `POST /analysis/phonological`             → Phonologische Analyse (Audio)
- `POST /analysis/phonological-text`        → Phonologische Analyse (Text)
- `POST /analysis/compare`                  → Berichte vergleichen
- `POST /suggest`                           → Textvorschläge

## Report-Typen

`befundbericht` | `therapiebericht_kurz` | `therapiebericht_lang` | `abschlussbericht`

## Lokale Entwicklung

```bash
# Backend
cd backend && pip install -r requirements.txt -r requirements-dev.txt
uvicorn backend.main:app --reload --port 8001

# Frontend
cd frontend && npm install && npm run dev

# Tests
cd backend && python -m pytest
cd frontend && npm test
```

Env-Vars: `GROQ_API_KEY`, `ALLOWED_ORIGINS`, `KV_REST_API_URL`, `KV_REST_API_TOKEN`, `DATABASE_URL`

## Deploy

```bash
vercel deploy
```

## Wichtige Hinweise

- Session-State in **Upstash Redis** (Fernet-encrypted, 24h TTL)
- Reports persistent in **Neon PostgreSQL** via SQLModel
- Max Upload: 25 MB (Audio), 10 MB (Material), max 5 Materialien pro Session
- Session-IDs: 12-Zeichen Hex-Strings (validated via regex)
- Frontend features in `features/` als Module organisiert (chat, report, phonology, therapy-plan, compare, suggest, history, soap)
- `sys.path.insert(0, backend/)` in main.py → Imports ohne `backend.`-Prefix (Tests müssen gleichen Pfad nutzen)
- Rate Limiting via slowapi + Redis
- Linting: ruff (backend), ESLint (frontend); Type-Check: mypy (backend), tsc (frontend)
