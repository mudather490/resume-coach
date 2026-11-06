"""Groq chat client (OpenAI-compatible API).

Groq hosts Qwen 3.8 27B and is used as the hosted chat provider on Vercel,
where no local Ollama is available. Requests are plain HTTP via ``requests``
so the deployment needs no extra SDK.
"""

import requests
from fastapi import HTTPException

from backend.config import (
    GROQ_API_KEY,
    GROQ_CHAT_MODEL,
    GROQ_MAX_TOKENS,
    GROQ_REASONING_EFFORT,
    GROQ_TIMEOUT,
)

BASE_URL = "https://api.groq.com/openai/v1"


def _error_text(resp) -> str:
    try:
        body = resp.json()
        if isinstance(body, dict):
            error = body.get("error")
            if isinstance(error, dict):
                return str(error.get("message") or error)
            if error:
                return str(error)
        return str(body)
    except Exception:
        return (resp.text or "").strip() or str(resp.status_code)


def _check_config():
    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=503,
            detail=(
                "LLM_PROVIDER=groq but GROQ_API_KEY is not set. "
                "Get a key at https://console.groq.com/keys and add it to the "
                "environment (backend/.env locally, Project Settings on Vercel)."
            ),
        )


def _fail(e: Exception):
    if isinstance(e, requests.exceptions.Timeout):
        raise HTTPException(
            status_code=504,
            detail=(
                f"Groq did not answer within {GROQ_TIMEOUT:.0f}s "
                f"(model: {GROQ_CHAT_MODEL}). Try again or lower GROQ_MAX_TOKENS."
            ),
        )
    if isinstance(e, requests.exceptions.ConnectionError):
        raise HTTPException(
            status_code=503,
            detail=(
                "Could not reach Groq at https://api.groq.com. "
                "Check the deployment's outbound network access and try again."
            ),
        )

    response = getattr(e, "response", None)
    status = getattr(response, "status_code", None)
    detail = _error_text(response) if response is not None else str(e)
    hints = {
        400: " The request was rejected — check GROQ_CHAT_MODEL and the optional GROQ_* settings.",
        401: " GROQ_API_KEY is invalid or revoked.",
        403: " The key does not have access to this model.",
        404: f" Model {GROQ_CHAT_MODEL!r} was not found. Preview models can be renamed or retired; set GROQ_CHAT_MODEL to an available model.",
        429: " Groq rate limit reached. Wait a moment and retry.",
    }
    hint = hints.get(status, "")
    raise HTTPException(
        status_code=502,
        detail=(
            f"Groq API request failed"
            f"{f' (HTTP {status})' if status else ''}: {detail}.{hint}"
        ),
    )


def chat(messages: list[dict], temperature: float = 0.3) -> str:
    _check_config()

    body = {
        "model": GROQ_CHAT_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_completion_tokens": GROQ_MAX_TOKENS,
    }
    if GROQ_REASONING_EFFORT:
        # Instruct mode ("none") avoids a long hidden reasoning phase, which
        # keeps resume coaching fast and predictable. "hidden" keeps any
        # reasoning out of the answer text. Leave GROQ_REASONING_EFFORT empty
        # when pointing GROQ_CHAT_MODEL at a non-reasoning model.
        body["reasoning_effort"] = GROQ_REASONING_EFFORT
        body["reasoning_format"] = "hidden"

    try:
        resp = requests.post(
            f"{BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=GROQ_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
        choices = payload.get("choices") or []
        if not choices:
            raise HTTPException(
                status_code=502,
                detail=f"Groq returned no choices: {payload}",
            )

        choice = choices[0]
        content = ((choice.get("message") or {}).get("content") or "").strip()
        if not content:
            raise HTTPException(
                status_code=502,
                detail=(
                    "Groq returned an empty response. "
                    f"finish_reason={choice.get('finish_reason')!r}, "
                    f"model={GROQ_CHAT_MODEL!r}."
                ),
            )
        if choice.get("finish_reason") == "length":
            content += (
                "\n\n_(The answer reached the output limit and may be cut off. "
                "Raise GROQ_MAX_TOKENS for a longer reply.)_"
            )
        return content
    except HTTPException:
        raise
    except Exception as e:
        _fail(e)
