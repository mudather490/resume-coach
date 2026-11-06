from dotenv import load_dotenv
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# True on Vercel Functions (set automatically by the platform).
ON_VERCEL = bool(os.getenv("VERCEL"))

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "embeddinggemma:latest")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "llama3.2:3b")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "1200"))
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "1024"))
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()  # ollama | gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.5-flash")
GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "text-embedding-004")

# Local state (active resume JSON + sessions SQLite).
# Kept as CHROMA_PATH for backwards compatibility with existing installs: the
# old ./chroma_db/active_resume.json is read in place, so an uploaded resume
# survives the switch away from ChromaDB.
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
# Vercel's filesystem is read-only except /tmp, so fall back there. With an
# Upstash Redis integration configured, nothing is written to disk at all.
DATA_DIR = os.getenv("DATA_DIR", "/tmp/data" if ON_VERCEL else CHROMA_PATH)

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
TOP_K = int(os.getenv("TOP_K", "5"))
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
# Vercel Functions cap the request body at 4.5 MB.
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "4" if ON_VERCEL else "10"))
REVIEW_CONTEXT_CHARS = int(os.getenv("REVIEW_CONTEXT_CHARS", "24000"))

# Upstash Redis REST (auto-injected by the Vercel Marketplace integration).
KV_REST_API_URL = (
    os.getenv("KV_REST_API_URL") or os.getenv("UPSTASH_REDIS_REST_URL") or ""
)
KV_REST_API_TOKEN = (
    os.getenv("KV_REST_API_TOKEN") or os.getenv("UPSTASH_REDIS_REST_TOKEN") or ""
)
USE_KV = bool(KV_REST_API_URL and KV_REST_API_TOKEN)

# Local SQLite sessions database (ignored when Upstash Redis is configured).
_REPO_ROOT = os.path.dirname(BASE_DIR)
SESSIONS_DB_PATH = os.getenv(
    "SESSIONS_DB_PATH",
    "/tmp/data/sessions.db"
    if ON_VERCEL
    else os.path.join(_REPO_ROOT, "sessions.db"),
)
