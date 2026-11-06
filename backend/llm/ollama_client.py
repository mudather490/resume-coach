import requests
from fastapi import HTTPException
from backend.config import (
    OLLAMA_HOST,
    OLLAMA_EMBED_MODEL,
    OLLAMA_CHAT_MODEL,
    OLLAMA_TIMEOUT,
    OLLAMA_NUM_CTX,
    OLLAMA_NUM_PREDICT,
)


def is_reachable():
    """Fast probe — raises if Ollama is not answering."""
    requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5).raise_for_status()


def _response_text(resp) -> str:
    try:
        body = resp.json()
        if isinstance(body, dict) and body.get("error"):
            return str(body["error"])
        return str(body)
    except Exception:
        return (resp.text or "").strip() or str(resp.status_code)


def _fail(e: Exception):
    if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
        if isinstance(e, requests.exceptions.Timeout):
            raise HTTPException(
                status_code=504,
                detail=(
                    f"Ollama did not answer within {OLLAMA_TIMEOUT:.0f}s on {OLLAMA_HOST}. "
                    "This usually means the model is generating on CPU and is too slow.\n"
                    "Fix:\n"
                    "1. Raise the limit in backend/.env:  OLLAMA_TIMEOUT=1200\n"
                    "2. Or lower the output size:  OLLAMA_NUM_PREDICT=512\n"
                    f"3. Or pull a smaller model and set OLLAMA_CHAT_MODEL "
                    f"(e.g. ollama pull llama3.2:1b)\n"
                    "4. Or switch provider:  LLM_PROVIDER=gemini  +  GEMINI_API_KEY=your_key"
                ),
            )
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

    status = getattr(getattr(e, "response", None), "status_code", None)
    detail = _response_text(e.response) if getattr(e, "response", None) is not None else str(e)
    raise HTTPException(
        status_code=502,
        detail=(
            f"Ollama returned an error"
            f"{f' (HTTP {status})' if status else ''}: {detail}\n"
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
                timeout=OLLAMA_TIMEOUT,
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
            json={
                "model": OLLAMA_CHAT_MODEL,
                "messages": messages,
                "stream": False,
                "keep_alive": "30m",
                "options": {
                    "temperature": temperature,
                    "num_ctx": OLLAMA_NUM_CTX,
                    "num_predict": OLLAMA_NUM_PREDICT,
                },
            },
            timeout=OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        body = resp.json()
        content = (body.get("message") or {}).get("content")
        if not content:
            raise HTTPException(
                status_code=502,
                detail=f"Ollama returned an empty response: {_response_text(resp)}",
            )
        return content
    except HTTPException:
        raise
    except Exception as e:
        _fail(e)
