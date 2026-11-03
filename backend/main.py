from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from backend.db.chroma_client import get_client
from backend.config import FRONTEND_URL

app = FastAPI(title="RAG Chatbot", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],
    # Vercel assigns wildcard subdomains per deploy: app-name-team.vercel.app
    allow_origin_regex=r"https://[a-z0-9-]+\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    get_client()

from backend.ingest.router import router as ingest_router
from backend.chat.router import router as chat_router
from backend.sessions.router import router as sessions_router

app.include_router(ingest_router, prefix="/ingest", tags=["ingest"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(sessions_router, prefix="/sessions", tags=["sessions"])

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url=FRONTEND_URL)

@app.get("/health")
def health():
    return {"status": "ok"}
