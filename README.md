# Logopädie Report Agent

An AI-powered tool that records speech therapy sessions and automatically generates structured medical reports using Groq's Whisper and Llama models.

## Demo

Record audio → AI transcribes via Whisper → Llama-3.3-70b extracts structured data → Renders a professional report card.

![Report Card](docs/screenshot.png)

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, Tailwind CSS v4, TypeScript |
| Backend | FastAPI (Python 3.12), Pydantic v2 |
| AI | Groq API — Whisper large-v3 (STT) + Llama-3.3-70b (NLP) |
| Deploy | Vercel (monorepo via `vercel.json` Services) |

## Architecture

```
Browser (MediaRecorder API)
  └─► POST /api/process-audio (multipart audio)
        └─► FastAPI
              ├─► Groq Whisper  → transcript
              └─► Groq Llama    → MedicalReport JSON
                    └─► Next.js UI (ReportCard)
```

## Report Schema

```json
{
  "patient_pseudonym": "Patient-A1",
  "symptoms": ["Stottern", "Artikulationsstörung"],
  "therapy_progress": "Deutliche Verbesserung nach 3 Sitzungen.",
  "prognosis": "Günstige Prognose bei regelmäßiger Therapie."
}
```

## Local Setup

### Prerequisites
- Node.js 20+
- Python 3.12+
- [Groq API key](https://console.groq.com/keys) (free tier available)

### 1. Clone & install

```bash
git clone https://github.com/ucarsinan/logopaedie-report-agent.git
cd logopaedie-report-agent

# Backend
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install
```

### 2. Configure environment

```bash
cp .env.example .env
# Add your GROQ_API_KEY to .env
```

### 3. Run

```bash
# Terminal 1 — Backend
uvicorn backend.main:app --reload

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Open [http://localhost:3000](http://localhost:3000), allow microphone access, and record a session.

## Deployment (Vercel)

This project uses [Vercel Services](https://vercel.com/docs/services) to deploy the Next.js frontend and FastAPI backend as a single monorepo.

```bash
vercel deploy
```

Set `GROQ_API_KEY` and `ALLOWED_ORIGINS` in Vercel project environment variables.

## License

MIT
