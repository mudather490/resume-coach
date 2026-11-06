"""LLM provider resolution.

Local (default):      LLM_PROVIDER=ollama -> uses local Ollama; if Ollama is
                      not reachable and GEMINI_API_KEY is set, falls back to
                      Gemini automatically.
Hosted (Vercel flow): LLM_PROVIDER=gemini + GEMINI_API_KEY on the backend host
                      (no local Ollama on a server).
"""
from fastapi import HTTPException

from backend.config import GEMINI_API_KEY, LLM_PROVIDER


def _ollama():
    from backend.llm import ollama_client as module
    return module


def _gemini():
    from backend.llm import gemini_client as module
    return module


NO_PROVIDER_DETAIL = (
    "No LLM provider is available. Fix with ONE of:\n"
    "1. Start Ollama:  ollama serve  (models: ollama list)\n"
    "2. Or set in backend/.env:  LLM_PROVIDER=gemini  and  GEMINI_API_KEY=your_key"
)

NO_LLM_DETAIL = (
    "The chat request failed on the active LLM provider.\n"
    "Local: start Ollama with  ollama serve  and set OLLAMA_CHAT_MODEL in backend/.env to a "
    "pulled model (ollama pull llama3.2:3b).\n"
    "Cloud: set  LLM_PROVIDER=gemini  +  GEMINI_API_KEY=your_key  in backend/.env."
)


def _fusing_gemini() -> bool:
    return LLM_PROVIDER == "gemini"


def _preserve(exc: HTTPException) -> HTTPException:
    """Re-raise the provider's real error instead of masking it.

    The previous implementation replaced every Ollama failure (wrong model,
    timeout, out-of-memory, ...) with the generic NO_LLM_DETAIL message, which
    hid the actual cause. Only fall back to the generic hint when the provider
    gave us no detail at all.
    """
    detail = getattr(exc, "detail", None) or NO_LLM_DETAIL
    status = getattr(exc, "status_code", None) or 502
    return HTTPException(status_code=status, detail=detail)


def ollama_reachable() -> bool:
    try:
        _ollama().is_reachable()
        return True
    except Exception:
        return False


def provider_status() -> dict:
    return {
        "config_provider": LLM_PROVIDER,
        "active_provider": "gemini" if _fusing_gemini() else "ollama",
        "ollama_reachable": ollama_reachable(),
        "gemini_key_set": bool(GEMINI_API_KEY),
    }


def embed(texts: list[str]) -> list[list[float]]:
    if _fusing_gemini():
        return _gemini().embed(texts)
    if ollama_reachable():
        try:
            return _ollama().embed(texts)
        except HTTPException as e:
            if GEMINI_API_KEY:
                return _gemini().embed(texts)
            raise _preserve(e)
    if GEMINI_API_KEY:
        return _gemini().embed(texts)
    raise HTTPException(status_code=503, detail=NO_PROVIDER_DETAIL)


def chat(messages: list[dict], temperature: float = 0.3) -> str:
    if _fusing_gemini():
        return _gemini().chat(messages, temperature)
    if ollama_reachable():
        try:
            return _ollama().chat(messages, temperature)
        except HTTPException as e:
            if GEMINI_API_KEY:
                return _gemini().chat(messages, temperature)
            raise _preserve(e)
    if GEMINI_API_KEY:
        return _gemini().chat(messages, temperature)
    raise HTTPException(status_code=503, detail=NO_PROVIDER_DETAIL)


__all__ = ["embed", "chat", "provider_status", "ollama_reachable"]
