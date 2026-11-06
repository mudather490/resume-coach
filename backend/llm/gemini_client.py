import requests
from fastapi import HTTPException
from backend.config import (
    GEMINI_API_KEY,
    GEMINI_CHAT_MODEL,
    GEMINI_EMBED_MODEL,
)

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

def _fail(e: Exception):
    status = getattr(getattr(e, "response", None), "status_code", None)
    hint = ""
    if status in (400, 403, 404):
        hint = (
            " Check your GEMINI_API_KEY and model names"
            f" (chat: {GEMINI_CHAT_MODEL}, embed: {GEMINI_EMBED_MODEL}) and"
            " that the key has access to the Generative Language API."
        )
    raise HTTPException(
        status_code=502,
        detail=f"Gemini API request failed: {e}.{hint}",
    )

def _check_config():
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY is not set. "
                   "Get a key at https://aistudio.google.com/apikey and add it to the "
                   "environment (backend/.env locally, Project Settings on Vercel).",
        )

def embed(texts: list[str]) -> list[list[float]]:
    _check_config()
    try:
        out: list[list[float]] = []
        for i in range(0, len(texts), 100):  # batch API accepts up to 100 requests
            batch = [
                {
                    "model": f"models/{GEMINI_EMBED_MODEL}",
                    "content": {"parts": [{"text": t}]},
                }
                for t in texts[i : i + 100]
            ]
            resp = requests.post(
                f"{BASE_URL}/models:batchEmbedContents",
                params={"key": GEMINI_API_KEY},
                json={"requests": batch},
                timeout=120,
            )
            resp.raise_for_status()
            out.extend(r["values"] for r in resp.json()["embeddings"])
        return out
    except HTTPException:
        raise
    except Exception as e:
        _fail(e)

def chat(messages: list[dict], temperature: float = 0.3) -> str:
    _check_config()
    try:
        contents = []
        system_instruction = None
        for m in messages:
            if m["role"] == "system":
                system_instruction = {"parts": [{"text": m["content"]}]}
                continue
            contents.append(
                {
                    "role": "model" if m["role"] == "assistant" else "user",
                    "parts": [{"text": m["content"]}],
                }
            )
        body: dict = {"contents": contents, "generationConfig": {"temperature": temperature}}
        if system_instruction:
            body["systemInstruction"] = system_instruction
        resp = requests.post(
            f"{BASE_URL}/models/{GEMINI_CHAT_MODEL}:generateContent",
            params={"key": GEMINI_API_KEY},
            json=body,
            timeout=120,
        )
        resp.raise_for_status()
        candidates = resp.json().get("candidates", [])
        if not candidates:
            return "No answer received from the model."
        parts = candidates[0].get("content", {}).get("parts", [])
        return "\n".join(p.get("text", "") for p in parts).strip()
    except Exception as e:
        _fail(e)
