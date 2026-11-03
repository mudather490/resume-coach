# Resume Coach — Local (ChromaDB + Ollama Native)

A PDF **resume** chatbot: upload your resume/CV, then chat with a coach that
reviews/develops it, expands its content, or shortens it. Anything unrelated
to resumes is declined. Runs fully local on Windows without Docker.

## Prerequisites

1. **Ollama** — download and install from https://ollama.com (Windows installer)
2. **Python 3.10+**
3. **Node.js 18+**

## Pull Ollama models (run once in PowerShell)

```powershell
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

## Start Ollama server

Ollama runs automatically after install. Verify it's running:
```powershell
ollama list
```
It serves on http://localhost:11434

## Backend

```powershell
cd E:\frist_rag
copy backend\.env.example backend\.env
python -m venv backend\.venv
backend\.venv\Scripts\activate
pip install -r backend\requirements.txt
uvicorn backend.main:app --reload --port 8000
```

Note: the backend uses `backend.*` package imports, so uvicorn must run from the project root (`E:\frist_rag`), not from inside `backend\`.

## Frontend (new terminal)

```powershell
cd E:\frist_rag\frontend
npm install
npm run dev
```

Open http://localhost:3000

## Architecture

Next.js frontend → FastAPI backend → LLM provider (embed/chat) → ChromaDB (local vector store, ./chroma_db)

## Resume-specific behavior

- **Upload gate** — `backend/resume/guardrails.py::is_resume_document` checks extracted
  PDF text (section headings, contact info, education tokens, date ranges vs. paper/
  invoice markers). Non-resume PDFs are rejected with HTTP 400.
- **Chat gate** — `is_resume_related` screens every message: a keyword allow/deny screen
  in Python first; ambiguous messages go to a one-letter LLM classifier. Off-topic requests
  get a "resume coach only" refusal and skip retrieval entirely.
- **Intent routing** — `classify_intent` maps messages to `review` (review & develop
  suggestions), `expand` (STAR detail), `shorten` (one-page condensing) or `general`.
  The frontend also sends explicit intents from the quick-action chips.
- **Coaching rules** — `backend/resume/prompts.py` encodes professional standards:
  Action + Context + Result / STAR bullets, strong action verbs, quantified achievements,
  no invented facts (missing numbers become `[placeholders]`), ATS-friendly formatting.

## LLM providers: Local = Ollama · Vercel = Gemini

Local development uses **Ollama** (already the default) — nothing to configure.

On a hosted backend (the Vercel flow), switch to **Gemini** by setting on the
backend host:

- `LLM_PROVIDER=gemini`
- `GEMINI_API_KEY=your_key` (free: https://aistudio.google.com/apikey)
- Optional: `GEMINI_CHAT_MODEL` (default `gemini-2.5-flash`), `GEMINI_EMBED_MODEL` (default `text-embedding-004`)

Two conveniences:

- **Auto-fallback**: with `LLM_PROVIDER=ollama` locally, if Ollama is not running
  and a `GEMINI_API_KEY` is set in `backend/.env`, the backend silently uses
  Gemini instead of failing.
- **Self-diagnostics**: `GET /health` reports the active provider, whether
  Ollama is reachable, and whether a Gemini key is configured.

## Endpoints

- POST /ingest — upload a resume PDF (non-resumes are rejected)
- DELETE /ingest/reset — clear the resume index (e.g. to remove pre-gate documents)
- POST /chat — talk to the coach, optional `intent` field: `review | expand | shorten | general | auto`
- GET /sessions/{id} — conversation history
- GET /sessions — list sessions
- GET /health

## Deploying to Vercel

Vercel hosts the **frontend only**. The FastAPI backend needs a server with a
persistent disk for ChromaDB — it cannot run on Vercel serverless (use Railway,
Render, Fly.io or a VM for the backend).

### 1. Deploy the frontend to Vercel (dashboard)

1. Go to https://vercel.com/new and **Import** the GitHub repo `mudather490/resume-coach`.
2. Under **Build & Output Settings → Root Directory**, set `frontend`
   (the repo root has no package.json; the Next.js app lives in `frontend/`).
   Framework preset auto-detects as **Next.js**.
3. Add the environment variable:
   - `NEXT_PUBLIC_API_BASE` = your backend's public URL (e.g. `https://your-backend.up.railway.app`)
4. Click **Deploy**. Every push to `main` of GitHub re-deploys automatically.

### 2. Host the backend (persistent disk required)

On the backend host, set these environment vars:

- `LLM_PROVIDER=gemini` + `GEMINI_API_KEY` (no local Ollama on a server —
  get a key at https://aistudio.google.com/apikey)
- `FRONTEND_URL=https://your-app.vercel.app` (CORS allowlist — accept the real
  domains Vercel assigns, including the `-*.vercel.app` preview domains by
  keeping the wildcard entry)
- `CHROMA_PATH=/data/chroma_db` → **mount a persistent volume/disk** at that
  path; anything under it survives restarts. Railway: Service → Volumes;
  Render: Disk; Fly.io: `fly volumes`.

If the volume works, uploaded resumes stay indexed across deploys and restarts.
