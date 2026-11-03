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

## LLM providers

Set in `backend/.env`:

- **Ollama** (default, fully local): `LLM_PROVIDER=ollama` + `OLLAMA_HOST`, `OLLAMA_CHAT_MODEL`, `OLLAMA_EMBED_MODEL`
- **Gemini** (hosted, for deployments without Ollama):
  - Get a free API key: https://aistudio.google.com/apikey
  - `LLM_PROVIDER=gemini`
  - `GEMINI_API_KEY=your_key`
  - Optional: `GEMINI_CHAT_MODEL` (default `gemini-2.5-flash`), `GEMINI_EMBED_MODEL` (default `text-embedding-004`)

## Endpoints

- POST /ingest — upload a resume PDF (non-resumes are rejected)
- POST /chat — talk to the coach, optional `intent` field: `review | expand | shorten | general | auto`
- GET /sessions/{id} — conversation history
- GET /sessions — list sessions
- GET /health

## Deploying to Vercel

Vercel hosts the **frontend only**. The FastAPI backend needs a server with a
persistent disk for ChromaDB (it runs fine on Railway, Render, Fly.io or a VM —
not on Vercel serverless).

1. Deploy `frontend/` to Vercel. Set env var `NEXT_PUBLIC_API_BASE` to your
   backend's public URL (e.g. `https://your-backend.up.railway.app`).
2. On the backend host, set:
   - `FRONTEND_URL=https://your-app.vercel.app` (CORS)
   - `LLM_PROVIDER=gemini` + `GEMINI_API_KEY` (no local Ollama on a server)
   - `CHROMA_PATH=/data/chroma_db` (a mounted/persistent volume)

## Vercel note

ChromaDB and Ollama run locally and cannot be hosted on Vercel serverless.
For Vercel, use a hosted backend (persistent disk) + `LLM_PROVIDER=gemini`
and deploy the Next.js frontend with `NEXT_PUBLIC_API_BASE` pointed at it.
