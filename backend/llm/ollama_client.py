import requests
from fastapi import HTTPException
from backend.config import OLLAMA_HOST, OLLAMA_EMBED_MODEL, OLLAMA_CHAT_MODEL

def _fail(e: Exception):
    raise HTTPException(
        status_code=502,
        detail=f"Ollama at {OLLAMA_HOST} is unreachable or returned an error: {e}",
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
