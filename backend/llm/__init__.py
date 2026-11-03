from backend.config import LLM_PROVIDER

if LLM_PROVIDER == "gemini":
    from backend.llm.gemini_client import embed, chat
else:
    from backend.llm.ollama_client import embed, chat

__all__ = ["embed", "chat"]
