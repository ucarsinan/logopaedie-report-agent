# Logopädie Report Agent

AI-powered tool for speech therapists: guided anamnesis interviews, automatic structured report generation, therapy plans, SOAP notes, and phonological analysis — all powered by Groq's Whisper and Llama models.

## Features

- **Guided Anamnesis** — AI-led interview that collects patient data step by step (text or voice)
- **Report Generation** — Befundbericht, Therapiebericht (kurz/lang), Abschlussbericht
- **Therapy Plans** — ICF-based therapy planning with phases, goals, and milestones
- **SOAP Notes** — Structured clinical documentation
- **Phonological Analysis** — Audio or text-based phonological process detection
- **Report Comparison** — Side-by-side comparison of two reports
- **PDF Export** — Download reports as formatted PDFs
- **Session History** — Browse and filter previously generated reports

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, Tailwind CSS v4, TypeScript |
| Backend | FastAPI, Python 3.12, Pydantic v2, SQLModel |
| AI | Groq API — Whisper large-v3 (STT) + Llama-3.3-70b (NLP) |
| Persistence | Upstash Redis (sessions), Neon PostgreSQL (reports) |
| CI/CD | GitHub Actions (lint, typecheck, test) |
| Deploy | Vercel Services (monorepo) |

## Architecture

```
Browser (React 19)
  ├─► POST /sessions → create session
  ├─► POST /sessions/{id}/chat → guided anamnesis (text)
  ├─► POST /sessions/{id}/audio → guided anamnesis (voice via Whisper)
  ├─► POST /sessions/{id}/upload → attach materials (PDF, DOCX, TXT)
  ├─► POST /sessions/{id}/generate → generate report (→ PostgreSQL)
  ├─► POST /sessions/{id}/therapy-plan → therapy plan
  ├─► POST /sessions/{id}/soap → SOAP notes
  ├─► POST /analysis/phonological → phonological analysis
  ├─► GET  /reports → session history (paginated)
  └─► GET  /reports/{id}/pdf → PDF download
```

```
backend/
├── main.py              # FastAPI app + exception handlers
├── routers/             # 9 APIRouter modules
├── services/            # 11 business logic services
├── models/              # Pydantic schemas + SQLModel tables
├── middleware/           # Auth + rate limiting
└── tests/               # 35 pytest tests

frontend/src/
├── features/            # 8 feature modules (chat, report, phonology, ...)
├── components/          # Shared UI components
├── providers/           # SessionProvider, ThemeProvider
├── hooks/               # Custom hooks
├── types/               # Centralized TypeScript types
└── lib/api.ts           # API client (20+ endpoints)
```

## Local Setup

### Prerequisites
- Node.js 22+
- Python 3.12+
- [Groq API key](https://console.groq.com/keys) (free tier available)

### 1. Clone & install

```bash
git clone https://github.com/ucarsinan/logopaedie-report-agent.git
cd logopaedie-report-agent

# Backend
cd backend && pip install -r requirements.txt -r requirements-dev.txt

# Frontend
cd frontend && npm install
```

### 2. Configure environment

```bash
cp .env.example .env
# Required: GROQ_API_KEY
# Optional: KV_REST_API_URL, KV_REST_API_TOKEN (Upstash Redis)
#           DATABASE_URL (Neon PostgreSQL)
```

### 3. Run

```bash
# Terminal 1 — Backend
cd backend && uvicorn backend.main:app --reload --port 8001

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Open [http://localhost:3000](http://localhost:3000), allow microphone access, and start a session.

### 4. Tests

```bash
cd backend && python -m pytest          # 35 backend tests
cd frontend && npm test                  # frontend component tests
```

## Deployment (Vercel)

This project uses [Vercel Services](https://vercel.com/docs/services) to deploy the Next.js frontend and FastAPI backend as a single monorepo.

```bash
vercel deploy
```

Environment variables in Vercel: `GROQ_API_KEY`, `ALLOWED_ORIGINS`, `KV_REST_API_URL`, `KV_REST_API_TOKEN`, `DATABASE_URL`, `JWT_SECRET`, `SERVICE_TOKEN`, `SESSION_ENCRYPTION_KEY`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `BACKEND_URL`

## License

MIT
