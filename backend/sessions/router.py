from fastapi import APIRouter, HTTPException
from backend.sessions.store import create_session, get_session, list_sessions, delete_session

router = APIRouter()

@router.post("")
def create_chat_session():
    session_id = create_session()
    return {"session_id": session_id}

@router.get("/{session_id}")
def get_session_messages(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.delete("/{session_id}")
def delete_chat_session(session_id: str):
    deleted = delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True}

@router.get("")
def list_chat_sessions():
    return list_sessions()
