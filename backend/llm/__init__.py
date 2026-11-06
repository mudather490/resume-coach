"""LLM provider resolution.

Chat provider (``LLM_PROVIDER``):
    ollama  local Ollama (default for development)
    groq    hosted Groq / Qwen (recommended on Vercel)
    gemini  hosted Google Gemini

Embedding provider (``EMBED_PROVIDER``) is independent, so chat can run on
Groq while Gemini produces embeddings:
    gemini | ollama

Locally, if Ollama is not reachable, chat falls back to Groq (when a Groq key
is present) and then to Gemini. On Vercel no Ollama probe is attempted.
"""

from fastapi import HTTPException

from backend.config import (
    EMBED_PROVIDER,
    GEMINI_API_KEY,
    GEMINI_EMBED_MODEL,
    GROQ_API_KEY,
    GROQ_CHAT_MODEL,
    LLM_PROVIDER,
    ON_VERCEL,
)


def _ollama():
    from backend.llm import ollama_client as module
    return module


def _gemini():
    from backend.llm import gemini_client as module
    return module


def _groq():
    from backend.llm import groq_client as module
    return module


NO_PROVIDER_DETAIL = (
    "No LLM provider is available. Fix with ONE of:\n"
    "1. Hosted (Vercel):  LLM_PROVIDER=groq  +  GROQ_API_KEY=your_key\n"
    "2. Hosted (Vercel):  LLM_PROVIDER=gemini  +  GEMINI_API_KEY=your_key\n"
    "3. Local:  start Ollama with  ollama serve  (models: ollama list)\n"
    "Embeddings:  GEMINI_API_KEY=your_key  +  EMBED_PROVIDER=gemini  "
    "(GEMINI_EMBED_MODEL=gemini-embedding-001)"
)

NO_LLM_DETAIL = (
    "The chat request failed on the active LLM provider.\n"
    "Local: start Ollama with  ollama serve  and set OLLAMA_CHAT_MODEL in backend/.env to a "
    "pulled model (ollama pull llama3.2:3b).\n"
    "Cloud: set  LLM_PROVIDER=groq  +  GROQ_API_KEY=your_key, or  "
    "LLM_PROVIDER=gemini  +  GEMINI_API_KEY=your_key."
)


def _preserve(exc: HTTPException) -> HTTPException:
    """Re-raise the provider's real error instead of masking it."""
    detail = getattr(exc, "detail", None) or NO_LLM_DETAIL
    status = getattr(exc, "status_code", None) or 502
    return HTTPException(status_code=status, detail=detail)


def ollama_reachable() -> bool:
    """Fast probe — false on Vercel, where no local Ollama can exist."""
    if ON_VERCEL:
        return False
    try:
        _ollama().is_reachable()
        return True
    except Exception:
        return False


def _chat_provider(reachable: bool | None = None) -> str:
    if LLM_PROVIDER in ("groq", "gemini"):
        return LLM_PROVIDER
    if reachable is None:
        reachable = ollama_reachable()
    if reachable:
        return "ollama"
    if GROQ_API_KEY:
        return "groq"
    if GEMINI_API_KEY:
        return "gemini"
    return "ollama"


def provider_status() -> dict:
    reachable = ollama_reachable()
    return {
        "config_provider": LLM_PROVIDER,
        "active_provider": _chat_provider(reachable),
        "chat_provider": _chat_provider(reachable),
        "embed_provider": EMBED_PROVIDER,
        "ollama_reachable": reachable,
        "gemini_key_set": bool(GEMINI_API_KEY),
        "groq_key_set": bool(GROQ_API_KEY),
        "groq_model": GROQ_CHAT_MODEL,
        "gemini_embed_model": GEMINI_EMBED_MODEL,
    }


def _fallback_chat(
    messages: list[dict],
    temperature: float,
    ollama_error: HTTPException | None,
) -> str:
    if GROQ_API_KEY:
        return _groq().chat(messages, temperature)
    if GEMINI_API_KEY:
        return _gemini().chat(messages, temperature)
    if ollama_error is not None:
        raise _preserve(ollama_error)
    raise HTTPException(status_code=503, detail=NO_PROVIDER_DETAIL)


def embed(texts: list[str]) -> list[list[float]]:
    if EMBED_PROVIDER == "gemini":
        return _gemini().embed(texts)
    if EMBED_PROVIDER == "ollama":
        if ollama_reachable():
            try:
                return _ollama().embed(texts)
            except HTTPException:
                if GEMINI_API_KEY:
                    return _gemini().embed(texts)
                raise
        if GEMINI_API_KEY:
            return _gemini().embed(texts)
        raise HTTPException(status_code=503, detail=NO_PROVIDER_DETAIL)
    raise HTTPException(
        status_code=400,
        detail=f"Unknown EMBED_PROVIDER={EMBED_PROVIDER!r}. Use gemini or ollama.",
    )


def chat(messages: list[dict], temperature: float = 0.3) -> str:
    if LLM_PROVIDER == "groq":
        return _groq().chat(messages, temperature)
    if LLM_PROVIDER == "gemini":
        return _gemini().chat(messages, temperature)
    if LLM_PROVIDER != "ollama":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown LLM_PROVIDER={LLM_PROVIDER!r}. "
                "Use ollama, groq or gemini."
            ),
        )

    if ollama_reachable():
        try:
            return _ollama().chat(messages, temperature)
        except HTTPException as e:
            return _fallback_chat(messages, temperature, e)
    return _fallback_chat(messages, temperature, None)


__all__ = ["embed", "chat", "provider_status", "ollama_reachable"]
