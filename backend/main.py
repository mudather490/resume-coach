import os
import sys

# Vercel's FastAPI service uses `entrypoint: vercel_entrypoint:app` with the
# backend/ folder as its root, while local development uses
# `uvicorn backend.main:app` from the repo root. Put the repo root on sys.path
# so the same `backend.*` imports work in both cases.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.chat.router import router as chat_router
from backend.ingest.router import router as ingest_router
from backend.sessions.router import router as sessions_router
from backend.web.routes import router as web_router

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="Resume Coach", version="1.0.0")

# The UI is served by this same process: /static/css, /static/js, ...
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(_BASE_DIR, "static")),
    name="static",
)

# HTML pages (/, /upload, /chat)
app.include_router(web_router)

# JSON API (kept for scripts, tests and future clients)
app.include_router(ingest_router, prefix="/ingest", tags=["ingest"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(sessions_router, prefix="/sessions", tags=["sessions"])


@app.get("/health")
def health():
    from backend.llm import provider_status

    return {"status": "ok", **provider_status()}
