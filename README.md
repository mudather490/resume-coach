# Resume Coach — Local (Ollama) · Vercel (Gemini, one project)

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
ollama pull embeddinggemma:latest
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
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt
# Windows: forces the selector event loop — the default Proactor loop can die with
# [WinError 64] and surface in the UI as "Backend unreachable"
python run_backend.py
```

On macOS/Linux, `uvicorn backend.main:app --reload --port 8000` works the same.

Note: the backend uses `backend.*` package imports, so uvicorn must run from the project root (`E:\frist_rag`), not from inside `backend\`.

## Frontend (new terminal)

```powershell
cd E:\frist_rag\frontend
npm install
npm run dev
```

Open http://localhost:3000

The browser calls the same-origin `/api/backend/*` proxy, which forwards to
`BACKEND_URL` (`http://localhost:8000` by default — set in `frontend/.env.local`).
This is the same code path used on Vercel.

## Architecture

Next.js frontend → same-origin `/api/backend` proxy → FastAPI backend → LLM provider
(chat) → active resume stored as JSON locally (`./chroma_db/active_resume.json`)
or in Upstash Redis on Vercel. Chat sends the whole resume as context, so no
vector index or embedding step is needed.

On Vercel both apps deploy as **one project** using [Vercel Services](#deploying-to-vercel):
`frontend/` (Next.js) and `backend/` (FastAPI) are separate services wired by
`vercel.json`, and the backend is reachable only through the frontend proxy.

## Resume-specific behavior

- **Fast upload** — the PDF is parsed, checked, chunked and saved in one pass; no
  embeddings or LLM calls run on the upload path, so it returns quickly.
- **Upload gate** — `backend/resume/guardrails.py::is_resume_document_fast` checks extracted
  PDF text (section headings, contact info, education tokens, date ranges vs. paper/
  invoice markers). Non-resume PDFs are rejected with HTTP 400.
- **Grounded answers** — the coach reads the whole active resume, not a search snippet.
  Questions about facts that aren't in the resume return `kind: "not_found"` and prompt
  the user to upload a different PDF; with no resume uploaded it returns `kind: "no_resume"`.
- **Blank start** — `/chat` always opens a fresh conversation with the three mode cards;
  earlier conversations stay under **Past chats**.
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
- **Slow CPU-only machines**: a full-resume review of `llama3.2:3b` on CPU can
  take several minutes. Tune in `backend/.env`:
  - `OLLAMA_TIMEOUT` (default `1200` seconds)
  - `OLLAMA_NUM_CTX` (default `8192`)
  - `OLLAMA_NUM_PREDICT` (default `1024`; lower for faster, shorter replies)

  Errors now surface the provider's real message (timeout, missing model, ...)
  instead of a generic "chat request failed" notice.

## Troubleshooting: "Backend unreachable"

The frontend banner (and chat/upload errors) ping `/health` and tell you the fix
for your environment:

- **Local dev** — the banner says the backend is down. Start it from the repo root:
  ```powershell
  python run_backend.py
  ```
  (`run_backend.py` forces the Windows selector event loop; the default
  Proactor loop can crash with `[WinError 64]` and take the server down.
  `uvicorn backend.main:app --reload --port 8000` works too on non-Windows.)
  and make sure Ollama is running for local answers (`ollama list`). CORS already
  allows `http://localhost:3000`.
- **Vercel (production)** — the browser calls the same-origin `/api/backend`
  proxy, which forwards to the private FastAPI service using the `BACKEND_URL`
  value injected by the service binding in `vercel.json`. If the banner appears,
  check the **backend** service logs in the deployment (Vercel → Project →
  Deployments → Functions) and that `LLM_PROVIDER=gemini` + `GEMINI_API_KEY` are
  set. Remove any old `NEXT_PUBLIC_API_BASE` from the project env — a
  `localhost` value is detected and reported explicitly.
- `NEXT_PUBLIC_API_BASE` still works as an optional override to call a backend
  directly from the browser (bypassing the proxy), but it is not needed.

## Endpoints

- POST /ingest — upload a resume PDF (non-resumes are rejected; replaces the active resume)
- GET /ingest/status — active resume filename/chunk count, or `has_resume: false`
- DELETE /ingest/reset — clear the resume index (e.g. to remove pre-gate documents)
- POST /chat — talk to the coach, optional `intent` field: `review | expand | shorten | general | auto`.
  Responses include `kind`: `answer | refusal | no_resume | not_found`
- GET /sessions/{id} — conversation history
- GET /sessions — list sessions
- GET /health

## Deploying to Vercel

The repo deploys as **one Vercel project** with two services declared in
`vercel.json` ([Vercel Services](https://vercel.com/docs/services), beta on all
plans):

| Service  | Root       | Framework | Notes |
| -------- | ---------- | --------- | ----- |
| frontend | `frontend/` | nextjs    | Public entry point |
| backend  | `backend/`  | fastapi   | Private; entrypoint `main:app` |

The FastAPI service is **private**. The Next.js app calls it through the
same-origin `/api/backend/*` proxy (`frontend/app/api/backend/[...path]/route.ts`),
which reads the `BACKEND_URL` the service binding injects. There is no CORS
setup and no `NEXT_PUBLIC_API_BASE` URL to configure.

### 1. Import the repository

1. Go to https://vercel.com/new and **Import** the GitHub repo.
2. **Root Directory = the repository root** — do **not** select `frontend/` or
   `backend/` (that is what produced the earlier one-framework deploy).
3. **Framework Preset = Services** (not Next.js, not FastAPI). `vercel.json`
   declares both services.
4. Click **Deploy**.

### 2. Environment variables

Project → **Settings → Environment Variables**:

- `LLM_PROVIDER=gemini`
- `GEMINI_API_KEY=your_key` (https://aistudio.google.com/apikey)
- Optional: `MAX_UPLOAD_MB=4` (Vercel caps request bodies at 4.5 MB)
- Optional: `GEMINI_CHAT_MODEL` (default `gemini-2.5-flash`)

Remove `NEXT_PUBLIC_API_BASE` if it exists — the same-origin proxy is the
default and a leftover `localhost` value is reported by the in-app banner.

### 3. Persistent storage (Upstash Redis)

Vercel Functions have an ephemeral `/tmp` only, so without storage the uploaded
resume and past chats reset after cold starts.

1. Project → **Storage** → **Upstash Redis** → connect it to Production
   (and Preview, if you use previews).
2. The integration injects `KV_REST_API_URL` / `KV_REST_API_TOKEN` (or the
   `UPSTASH_REDIS_REST_*` equivalents); both are supported.
3. Redeploy so the variables reach the backend service.

Without Upstash the app still works, but it falls back to ephemeral `/tmp`
storage and asks you to re-upload after the function goes cold.

### 4. Verify

- `https://<your-app>.vercel.app/api/backend/health` should report
  `"active_provider": "gemini"` (not `ollama`).
- Upload a PDF, then chat.

### Why the first attempt returned `500 FUNCTION_INVOCATION_FAILED`

A single Vercel project normally runs **one** framework, so importing this
monorepo offered either Next.js or FastAPI. Deploying the FastAPI half alone
crashed the function:

1. With the backend folder as the Root Directory, `main.py` imports
   `backend.config` but the `backend` package is only importable from the repo
   root → `ModuleNotFoundError` → 500 on every request.
2. Startup opened ChromaDB at `./chroma_db` and sessions at `sessions.db` — the
   Vercel filesystem is read-only → crash.
3. No `LLM_PROVIDER=gemini` / `GEMINI_API_KEY` was set, so it defaulted to
   Ollama, which does not exist on Vercel.

The Services setup above fixes all three: repo-root build, writable paths
(`/tmp`, or Upstash), and Gemini via environment variables.

### Fallback: host the backend separately (Docker)

If you prefer a separate backend host (Railway/Render/Fly.io), the root
`Dockerfile` builds the FastAPI service. Mount a volume at `/data` and set:

- `LLM_PROVIDER=gemini`, `GEMINI_API_KEY`
- `DATA_DIR=/data`
- `SESSIONS_DB_PATH=/data/sessions.db`
- `FRONTEND_URL=https://your-app.vercel.app` (CORS)

Then set `NEXT_PUBLIC_API_BASE=https://your-backend-host` in the Vercel
frontend project to bypass the proxy.

