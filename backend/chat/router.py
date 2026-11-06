from fastapi import APIRouter, HTTPException

from backend.config import REVIEW_CONTEXT_CHARS
from backend.llm import chat
from backend.db.store import get_active_doc, get_document_chunks
from backend.sessions.store import create_session, add_message, get_session
from backend.models.schemas import ChatRequest, ChatResponse
from backend.resume.prompts import (
    COACH_SYSTEM_PROMPT,
    INTENT_TASKS,
    REFUSAL_ANSWER,
    EMPTY_ANSWER_FALLBACK,
    NO_RESUME_ANSWER,
    NOT_IN_RESUME_ANSWER,
    NOT_FOUND_TOKEN,
)
from backend.resume.guardrails import (
    is_resume_related,
    classify_intent,
    sanitize_for_fence,
    strip_dismissive_preamble,
    looks_like_meta_answer,
    looks_like_missing_fact,
    asks_about_missing_fact,
)

router = APIRouter()

MAX_HISTORY_MESSAGES = 20
VALID_INTENTS = set(INTENT_TASKS.keys()) | {"auto"}


def _full_resume_context(active: dict) -> str:
    chunks = active.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        chunks = get_document_chunks(active["doc_id"])
    parts = []
    for c in chunks:
        page = c.get("page")
        label = f"[Resume page {page}] " if page is not None else ""
        parts.append(f"{label}{c.get('text', '')}")
    return "\n\n".join(parts)[:REVIEW_CONTEXT_CHARS]


@router.post("", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    if req.intent and req.intent not in VALID_INTENTS:
        raise HTTPException(status_code=400, detail=f"Unknown intent: {req.intent}")

    session_id = req.session_id or create_session()
    session = get_session(session_id)
    history = session["messages"][-MAX_HISTORY_MESSAGES:] if session else []

    active = get_active_doc()

    # Layer 1+2: decide scope before anything else. Refusals skip retrieval entirely.
    if not is_resume_related(req.message, history):
        answer = REFUSAL_ANSWER
        sources = []
        kind = "refusal"
    elif not active:
        answer = NO_RESUME_ANSWER
        sources = []
        kind = "no_resume"
    else:
        intent = req.intent if req.intent and req.intent != "auto" else classify_intent(req.message)

        # One active resume: use the whole document as context. This is both
        # more accurate for review/expand/shorten and avoids a slow embedding
        # round-trip on every message.
        context = _full_resume_context(active)
        sources = [{"doc_id": active["doc_id"], "page": None, "score": 1.0}]

        if intent == "general" and asks_about_missing_fact(req.message, context):
            answer = NOT_IN_RESUME_ANSWER
            sources = []
            kind = "not_found"
        else:
            # Layer 3: enforcement inside the coach system prompt.
            system = f"{COACH_SYSTEM_PROMPT}\n\n{INTENT_TASKS[intent]}"
            messages = [{"role": "system", "content": system}]
            messages.extend(history)
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"<<<USER>>>{sanitize_for_fence(req.message)}<<<END>>>\n\n"
                        f"RESUME CONTEXT:\n{context}"
                    ),
                }
            )
            answer = chat(messages, temperature=0.1 if intent != "general" else 0.2)

            missing = NOT_FOUND_TOKEN in answer or (
                intent == "general" and looks_like_missing_fact(answer)
            )
            if missing:
                answer = NOT_IN_RESUME_ANSWER
                sources = []
                kind = "not_found"
            else:
                answer = strip_dismissive_preamble(answer)
                if looks_like_meta_answer(answer):
                    answer = NOT_IN_RESUME_ANSWER
                    sources = []
                    kind = "not_found"
                else:
                    answer = answer or EMPTY_ANSWER_FALLBACK
                    kind = "answer"

    add_message(session_id, "user", req.message)
    add_message(session_id, "assistant", answer)

    return ChatResponse(answer=answer, sources=sources, session_id=session_id, kind=kind)


@router.get("/{session_id}")
def get_chat_history(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
