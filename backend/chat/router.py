from fastapi import APIRouter, HTTPException
from backend.config import TOP_K
from backend.llm import embed, chat
from backend.db.chroma_client import search
from backend.sessions.store import create_session, add_message, get_session
from backend.models.schemas import ChatRequest, ChatResponse
from backend.resume.prompts import COACH_SYSTEM_PROMPT, INTENT_TASKS, REFUSAL_ANSWER
from backend.resume.guardrails import (
    is_resume_related,
    classify_intent,
    sanitize_for_fence,
)

router = APIRouter()

MAX_HISTORY_MESSAGES = 20
VALID_INTENTS = set(INTENT_TASKS.keys()) | {"auto"}


@router.post("", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    if req.intent and req.intent not in VALID_INTENTS:
        raise HTTPException(status_code=400, detail=f"Unknown intent: {req.intent}")

    session_id = req.session_id or create_session()
    session = get_session(session_id)
    history = session["messages"][-MAX_HISTORY_MESSAGES:] if session else []

    # Layer 1+2: decide scope before anything else. Refusals skip retrieval entirely.
    if not is_resume_related(req.message, history):
        answer = REFUSAL_ANSWER
        sources = []
    else:
        intent = req.intent if req.intent and req.intent != "auto" else classify_intent(req.message)

        query_embedding = embed([req.message])[0]
        results = search(query_embedding, top_k=TOP_K)
        context = "\n\n".join(
            f"[Resume source: {r['doc_id']} page {r['page']}] {r['text']}" for r in results
        ) or "(no resume content indexed yet)"

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
        answer = chat(messages)
        sources = [{"doc_id": r["doc_id"], "page": r["page"], "score": r["score"]} for r in results]

    add_message(session_id, "user", req.message)
    add_message(session_id, "assistant", answer)

    return ChatResponse(answer=answer, sources=sources, session_id=session_id)

@router.get("/{session_id}")
def get_chat_history(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
