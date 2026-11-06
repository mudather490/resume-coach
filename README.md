# Resume Coach — one FastAPI app (Ollama local · Gemini hosted)

A PDF **resume** chatbot: upload your resume/CV, then chat with a coach that
reviews/develops it, expands its content, or shortens it. Anything unrelated to
resumes is declined.

The whole product — pages, static assets and JSON API — runs in **one FastAPI
process**. There is no Node.js build and no separate frontend service.

## Prerequisites

1. **Python 3.10+**
2. **Ollama** — https://ollama.com (optional if you use Gemini instead)
3. No Node.js required

## Pull Ollama models (run once in PowerShell, for local Ollama)

```powershell
ollama pull llama3.2:3b
ollama pull embeddinggemma:latest
```

Ollama serves on `http://localhost:11434`. Verify it with `ollama list`.

## Run locally

```powershell
cd E:\frist_rag
copy backend\.env.example backend\.env
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt

# Windows: forces the selector event loop — the default Proactor loop can die
# with [WinError 64] and surface as "Backend unreachable"
python run_backend.py
```

Open **http://localhost:8000**. The app serves its own UI:

- `/` — home
- `/upload` — upload a resume PDF
- `/chat` — the coach
- `/health` — provider diagnostics (JSON)
- `/docs` — FastAPI's generated API documentation

On macOS/Linux, `uvicorn backend.main:app --reload --port 8000` works the same.
Run uvicorn from the project root (not from inside `backend/`), because the code
uses `backend.*` package imports.

## Architecture

```
Browser
   │
   ▼
FastAPI (one process)
   ├── HTML pages      /  /upload  /chat        Jinja2 templates
   ├── Static files    /static/css, /static/js
   ├── JSON API        /ingest  /chat  /sessions  /health
   ├── PDF pipeline    pypdf → resume gate → chunks → active resume
   ├── Coach logic     guardrails + prompts + intent routing
   ├── LLM             Ollama (local) / Gemini (hosted)
   └── Storage         JSON file + SQLite  |  Upstash Redis on Vercel
```

- **One active resume** is stored as JSON in `DATA_DIR` (`./chroma_db` locally,
  `/tmp/data` on Vercel) or in Upstash Redis when its REST env vars exist.
- **Sessions** live in `sessions.db` (SQLite) locally, or Upstash Redis on
  Vercel.
- Chat sends the whole active resume as context, so no vector index or
  embedding call is needed.
- Assistant Markdown is rendered **server-side in Python** (`markdown-it-py`,
  raw HTML disabled) and returned as `answer_html`, so the browser needs no
  Markdown library.

## Resume-specific behavior

- **Fast upload** — the PDF is parsed, checked, chunked and saved in one pass;
  no embeddings or LLM calls run on the upload path.
- **Upload gate** — `backend/resume/guardrails.py::is_resume_document_fast`
  checks extracted PDF text (section headings, contact info, education tokens,
  date ranges vs. paper/invoice markers). Non-resume PDFs are rejected with
  HTTP 400.
- **Grounded answers** — the coach reads the whole active resume. Questions
  about facts that aren't in the resume return `kind: "not_found"`; with no
  resume uploaded it returns `kind: "no_resume"`.
- **Blank start** — `/chat` always opens a fresh conversation with the three
  mode cards; earlier conversations stay under **Past chats**.
- **Chat gate** — `is_resume_related` screens every message: a keyword
  allow/deny screen in Python first; ambiguous messages go to a one-letter LLM
  classifier. Off-topic requests get a "resume coach only" refusal and skip
  retrieval entirely.
- **Intent routing** — `classify_intent` maps messages to `review`, `expand`,
  `shorten` or `general`. The UI's quick actions send explicit intents.
- **Coaching rules** — `backend/resume/prompts.py` encodes professional
  standards: Action + Context + Result / STAR bullets, strong action verbs,
  quantified achievements, no invented facts (missing numbers become
  `[placeholders]`), ATS-friendly formatting.

## LLM providers: local = Ollama · hosted = Gemini

Local development uses **Ollama** by default.

On a hosted server, set:

- `LLM_PROVIDER=gemini`
- `GEMINI_API_KEY=your_key` (free: https://aistudio.google.com/apikey)
- Optional: `GEMINI_CHAT_MODEL` (default `gemini-2.5-flash`),
  `GEMINI_EMBED_MODEL`

Two conveniences:

- **Auto-fallback**: with `LLM_PROVIDER=ollama` locally, if Ollama is not
  running and a `GEMINI_API_KEY` is set, the backend silently uses Gemini.
- **Self-diagnostics**: `GET /health` reports the active provider, whether
  Ollama is reachable, and whether a Gemini key is configured.
- **Slow CPU-only machines**: a full-resume review of `llama3.2:3b` on CPU can
  take several minutes. Tune in `backend/.env`:
  - `OLLAMA_TIMEOUT` (default `1200` seconds)
  - `OLLAMA_NUM_CTX` (default `8192`)
  - `OLLAMA_NUM_PREDICT` (default `1024`)
  - `OLLAMA_CHAT_MODEL` (use `llama3.2:1b` for speed)

## Endpoints

HTML pages (server-rendered):

| Route | Purpose |
| --- | --- |
| `GET /` | Home page |
| `GET /upload` | Upload page |
| `GET /chat` | Chat page (blank start; history loads in place) |
| `GET /static/...` | CSS / JavaScript / icons |

JSON API (kept for scripts, tests and future clients):

| Route | Purpose |
| --- | --- |
| `POST /ingest` | Upload a resume PDF (non-resumes rejected; replaces the active resume) |
| `GET /ingest/status` | Active resume filename/chunk count, or `has_resume: false` |
| `DELETE /ingest/reset` | Clear the active resume |
| `POST /chat` | Talk to the coach. Optional `intent`: `review \| expand \| shorten \| general \| auto`. Response includes `kind` (`answer \| refusal \| no_resume \| not_found`) and `answer_html` |
| `GET /chat/{session_id}` | Conversation history (JSON) |
| `POST /sessions` | Create a session |
| `GET /sessions` | List sessions |
| `GET /sessions/{id}` | Messages (assistant messages include rendered `html`) |
| `DELETE /sessions/{id}` | Delete a session |
| `GET /health` | Provider / Ollama / Gemini status |

## Deploying to Vercel (one service)

`vercel.json` declares a **single** FastAPI service and rewrites all traffic to
it. Templates and static files are inside `backend/`, so they ship with the
function.

1. Go to https://vercel.com/new and **Import** the GitHub repo.
2. **Root Directory = the repository root** (not `backend/`).
3. **Framework Preset = Services** (the config declares the FastAPI service).
4. Deploy.

Then set these environment variables (Project → Settings → Environment
Variables):

- `LLM_PROVIDER=gemini`
- `GEMINI_API_KEY=your_key`
- Optional: `MAX_UPLOAD_MB=4` (Vercel caps request bodies at 4.5 MB)
- Optional: `GEMINI_CHAT_MODEL` (default `gemini-2.5-flash`)

### Persistent storage (Upstash Redis)

Vercel Functions have an ephemeral `/tmp` only, so without storage the uploaded
resume and past chats reset after cold starts.

1. Project → **Storage** → **Upstash Redis** → connect it to Production (and
   Preview if used).
2. The integration injects `KV_REST_API_URL` / `KV_REST_API_TOKEN` (or the
   `UPSTASH_REDIS_REST_*` equivalents); both are supported.
3. Redeploy so the variables reach the service.

Without Upstash the app still works, but it falls back to ephemeral `/tmp`
storage and asks you to re-upload after the function goes cold.

### Verify

- `https://<your-app>.vercel.app/` renders the home page.
- `https://<your-app>.vercel.app/health` reports `"active_provider": "gemini"`.
- `/upload` and `/chat` work; `/static/css/app.css` is served.
- Upload a PDF, then chat.

> If your Vercel plan rejects a single-service rewrite, the fallback is a tiny
> root `api/index.py` that exports the FastAPI `app` plus a rewrite of `/(.*)`
> to `/api/index`. The application code itself does not change.

## Docker / Render / Railway / VPS

The root `Dockerfile` builds the same single FastAPI app:

```powershell
docker build -t resume-coach .
docker run -p 8000:8000 `
  -e LLM_PROVIDER=gemini `
  -e GEMINI_API_KEY=your_key `
  -v resume_data:/data `
  resume-coach
```

Mount a volume at `/data` and keep:

- `LLM_PROVIDER=gemini`, `GEMINI_API_KEY`
- `DATA_DIR=/data`
- `SESSIONS_DB_PATH=/data/sessions.db`

Open `http://localhost:8000` (or your host URL).

## Troubleshooting

- **"Backend unreachable" in the UI** — the browser talks to the same origin,
  so this means the FastAPI process is down. Start it with
  `python run_backend.py`. Check `/health`.
- **Ollama errors** — run `ollama list` and make sure `OLLAMA_CHAT_MODEL`
  exists. The app now surfaces the provider's real error (missing model,
  timeout, …) in the chat bubble.
- **Uploads rejected** — the file must be a resume/CV PDF. The guard checks
  headings, contact details, education and date ranges.
- **Vercel cold starts lose the resume** — connect Upstash Redis; Vercel's
  filesystem is ephemeral.
- **CORS** — no longer needed: UI and API are the same origin. If you call the
  JSON API from another domain, add CORS middleware back in `backend/main.py`.

## Project layout

```
backend/
  main.py                 FastAPI app: static mount, page routes, API routers
  config.py               Paths, providers, limits
  web/
    routes.py             HTML page routes + Jinja filters
    markdown.py           Python Markdown rendering / plain-text stripping
  templates/              base, home, upload, chat, icon sprite
  static/                 app.css, api.js, upload.js, chat.js
  chat/router.py          Coach endpoint
  ingest/router.py        PDF upload + status/reset
  sessions/               Session storage + endpoints
  db/store.py             Active resume (file / Upstash Redis)
  llm/                    Ollama and Gemini clients with fallback
  resume/                 Guardrails and prompts
run_backend.py            Windows-safe launcher
Dockerfile                Single-image deployment
vercel.json               Single FastAPI service
```
