# Logopädie Report Agent – Claude Context

## Was dieses Projekt ist

AI-gestütztes Tool für Logopäden: Aufnahme von Therapiesitzungen → automatische strukturierte Berichte via Groq.
Portfolio-Projekt (Demo/Showcase), deployed auf Vercel als Monorepo mit Vercel Services.

## Stack

| Schicht | Tech |
|---|---|
| Frontend | Next.js 16, React 19, Tailwind CSS v4, TypeScript |
| Backend | FastAPI, Python 3.12, Pydantic v2 |
| AI | Groq API — Whisper large-v3 (STT) + Llama-3.3-70b (NLP) |
| Deploy | Vercel Services (`vercel.json` → `experimentalServices`) |

## Struktur

```
/
├── backend/           # FastAPI App (Python)
│   ├── main.py        # API-Entrypoint, alle Routen
│   ├── models/        # Pydantic-Schemas
│   └── services/      # Groq-Client, Report-Generator, Anamnesis-Engine, ...
├── frontend/          # Next.js App
│   └── src/app/
│       └── page.tsx   # Single-Page-App (Client Component)
└── vercel.json        # Services-Konfiguration
```

## API-Endpunkte (backend, routePrefix: /api)

- `GET  /health`
- `POST /sessions`                          → Session erstellen + Begrüßung
- `GET  /sessions/{id}`                     → Session-State lesen
- `POST /sessions/{id}/chat`                → Text-Chat (Anamnese)
- `POST /sessions/{id}/audio`               → Audio-Chat (Whisper → Chat)
- `POST /sessions/{id}/upload`              → Material-Upload (PDF, DOCX)
- `POST /sessions/{id}/generate`            → Bericht generieren
- `GET  /sessions/{id}/report`              → Generierten Bericht abrufen
- `POST /sessions/{id}/therapy-plan`        → Therapieplan generieren
- `POST /analysis/phonological`             → Phonologische Analyse (Audio)
- `POST /analysis/phonological-text`        → Phonologische Analyse (Text)
- `POST /analysis/compare`                  → Berichte vergleichen
- `POST /suggest`                           → Textvorschläge
- `POST /process-audio`                     → Legacy (Einzel-Transkription)

## Report-Typen

`befundbericht` | `therapiebericht_kurz` | `therapiebericht_lang` | `abschlussbericht`

## Lokale Entwicklung

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn backend.main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

Env: `GROQ_API_KEY`, `ALLOWED_ORIGINS=http://localhost:3000`

## Deploy

```bash
vercel deploy
```

Env-Vars in Vercel: `GROQ_API_KEY`, `ALLOWED_ORIGINS`

## Wichtige Hinweise

- Session-State ist **in-memory** (`session_store`) → kein Persist zwischen Deployments
- Max Upload: 25 MB (Audio), 10 MB (Material), max 5 Materialien pro Session
- Frontend ist eine Client Component (`"use client"`) — Single-Page-App
- `NEXT_PUBLIC_API_URL` für Frontend-Backend-Verbindung (default: `http://localhost:8000`)
