from fastapi import APIRouter, HTTPException

from backend.config import ATTACHMENT_CONTEXT_CHARS, REVIEW_CONTEXT_CHARS
from backend.llm import chat
from backend.db.store import get_active_doc, get_attachments, get_document_chunks
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
from backend.web.markdown import render_markdown

router = APIRouter()

MAX_HISTORY_MESSAGES = 20
VALID_INTENTS = set(INTENT_TASKS.keys()) | {"auto"}


def _attachment_text(attachment: dict) -> str:
    chunks = attachment.get("chunks")
    if not isinstance(chunks, list):
        return ""
    return "\n".join(c.get("text", "") for c in chunks if c.get("text"))


def _build_context(active: dict) -> str:
    """Resume text plus optional supporting documents, within one budget.

    The resume keeps priority: when supporting documents are present they get
    at most ATTACHMENT_CONTEXT_CHARS, and the resume gets the rest of
    REVIEW_CONTEXT_CHARS. This keeps the combined prompt inside the model
    window on local Ollama installs.
    """
    chunks = active.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        chunks = get_document_chunks(active["doc_id"])

    resume_parts = []
    for c in chunks:
        page = c.get("page")
        label = f"[Resume page {page}] " if page is not None else ""
        resume_parts.append(f"{label}{c.get('text', '')}")
    resume_text = "\n\n".join(resume_parts)

    attachments = get_attachments(active)
    attachment_budget = ATTACHMENT_CONTEXT_CHARS if attachments else 0
    resume_budget = max(0, REVIEW_CONTEXT_CHARS - attachment_budget)
    parts = [f"RESUME CONTEXT:\n{resume_text[:resume_budget]}"]

    if attachments:
        used = 0
        doc_parts = []
        for attachment in attachments:
            text = _attachment_text(attachment)
            if not text:
                continue
            remaining = ATTACHMENT_CONTEXT_CHARS - used
            if remaining <= 0:
                break
            snippet = text[:remaining]
            used += len(snippet)
            name = attachment.get("filename") or attachment.get("id") or "document"
            doc_parts.append(f"SUPPORTING DOCUMENT: {name}\n{snippet}")
        if doc_parts:
            parts.append("SUPPORTING DOCUMENTS:\n\n" + "\n\n".join(doc_parts))

    return "\n\n".join(parts)[:REVIEW_CONTEXT_CHARS]


def _context_sources(active: dict) -> list[dict]:
    """One source chip for the resume plus one per supporting document."""
    sources = [
        {
            "doc_id": active.get("filename") or active["doc_id"],
            "page": None,
            "score": 1.0,
            "kind": "resume",
        }
    ]
    for attachment in get_attachments(active):
        sources.append(
            {
                "doc_id": attachment.get("filename") or attachment.get("id"),
                "page": None,
                "score": 1.0,
                "kind": "attachment",
            }
        )
    return sources


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

        # One active resume plus its supporting documents: use the whole text
        # as context. This is both more accurate for review/expand/shorten/
        # build and avoids a slow embedding round-trip on every message.
        context = _build_context(active)
        sources = _context_sources(active)

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

    return ChatResponse(
        answer=answer,
        answer_html=render_markdown(answer),
        sources=sources,
        session_id=session_id,
        kind=kind,
    )


@router.get("/{session_id}")
def get_chat_history(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
