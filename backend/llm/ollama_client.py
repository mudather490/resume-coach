import requests
from fastapi import HTTPException
from backend.config import OLLAMA_HOST, OLLAMA_EMBED_MODEL, OLLAMA_CHAT_MODEL


def is_reachable():
    """Fast probe — raises if Ollama is not answering."""
    requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5).raise_for_status()

def _fail(e: Exception):
    msg = str(e.__cause__ or e)
    if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
        raise HTTPException(
            status_code=503,
            detail=(
                f"Ollama is not reachable on {OLLAMA_HOST}. Fix:\n"
                "1. Start it:  ollama serve\n"
                "2. Make sure the models exist:  ollama list  (pull with "
                f"\"ollama pull {OLLAMA_CHAT_MODEL}\")\n"
                "3. Or switch provider in backend/.env:  LLM_PROVIDER=gemini  +  GEMINI_API_KEY=your_key"
            ),
        )
    raise HTTPException(
        status_code=502,
        detail=(
            f"Ollama returned an error: {msg}\n"
            f"Check OLLAMA_CHAT_MODEL ({OLLAMA_CHAT_MODEL}) and OLLAMA_EMBED_MODEL "
            f"({OLLAMA_EMBED_MODEL}) exist in  ollama list."
        ),
    )

EMBED_BATCH_SIZE = 32

def embed(texts: list[str]) -> list[list[float]]:
    out: list[list[float]] = []
    try:
        for i in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = texts[i : i + EMBED_BATCH_SIZE]
            resp = requests.post(
                f"{OLLAMA_HOST}/api/embed",
                json={"model": OLLAMA_EMBED_MODEL, "input": batch},
                timeout=180,
            )
            resp.raise_for_status()
            out.extend(resp.json()["embeddings"])
        return out
    except HTTPException:
        raise
    except Exception as e:
        _fail(e)

def chat(messages: list[dict], temperature: float = 0.3) -> str:
    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            json={"model": OLLAMA_CHAT_MODEL, "messages": messages, "stream": False, "options": {"temperature": temperature}},
            timeout=180,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]
    except Exception as e:
        _fail(e)
