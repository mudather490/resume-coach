"""State storage for the active resume.

Two interchangeable backends:

* ``FileStore``  — local development. The active resume is a JSON file in
  ``DATA_DIR`` (default ``./chroma_db`` so existing installs keep working).
* ``RedisStore`` — Vercel. Upstash Redis over its REST API, selected
  automatically when the integration injects ``KV_REST_API_URL`` /
  ``KV_REST_API_TOKEN`` (or the ``UPSTASH_REDIS_REST_*`` equivalents).

Chat reads the whole resume from the active document, so no vector index is
needed; this module replaces the old ChromaDB client.
"""
import json
import os
import threading
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import requests

from backend.config import (
    DATA_DIR,
    KV_REST_API_TOKEN,
    KV_REST_API_URL,
    USE_KV,
)

ACTIVE_META_PATH = os.path.join(DATA_DIR, "active_resume.json")
_lock = threading.Lock()

# Redis keys
_ACTIVE_KEY = "resumecoach:active_resume"
_SESSION_INDEX = "resumecoach:sessions"
_SESSION_PREFIX = "resumecoach:session:"


# --------------------------------------------------------------------------- #
# Upstash Redis REST helpers
# --------------------------------------------------------------------------- #
def _redis(*args):
    """Run one Redis command through Upstash's REST API."""
    resp = requests.post(
        KV_REST_API_URL,
        headers={"Authorization": f"Bearer {KV_REST_API_TOKEN}"},
        json=list(args),
        timeout=10,
    )
    resp.raise_for_status()
    payload = resp.json()
    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(f"Redis error: {payload['error']}")
    return payload.get("result") if isinstance(payload, dict) else payload


def _kv_get(key: str):
    raw = _redis("GET", key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None


def _kv_set(key: str, value) -> None:
    _redis("SET", key, json.dumps(value, ensure_ascii=False))


# --------------------------------------------------------------------------- #
# Active resume document
# --------------------------------------------------------------------------- #
def _file_get_active() -> Optional[Dict]:
    with _lock:
        try:
            with open(ACTIVE_META_PATH, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None
    return meta if isinstance(meta, dict) and meta.get("doc_id") else None


def _file_set_active(meta: Dict) -> None:
    with _lock:
        os.makedirs(os.path.dirname(ACTIVE_META_PATH) or ".", exist_ok=True)
        tmp = ACTIVE_META_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)
        os.replace(tmp, ACTIVE_META_PATH)


def _file_clear_active() -> None:
    with _lock:
        try:
            os.remove(ACTIVE_META_PATH)
        except FileNotFoundError:
            pass


def get_active_doc() -> Optional[Dict]:
    """Return the active resume metadata (with its chunk text), or None."""
    meta = _kv_get(_ACTIVE_KEY) if USE_KV else _file_get_active()
    if not meta or not meta.get("doc_id"):
        return None
    return meta


def set_active_doc(meta: Dict) -> None:
    if USE_KV:
        _kv_set(_ACTIVE_KEY, meta)
    else:
        _file_set_active(meta)


def clear_active_doc() -> None:
    if USE_KV:
        _redis("DEL", _ACTIVE_KEY)
    else:
        _file_clear_active()


def chunk_count(meta: Optional[Dict]) -> int:
    """Number of chunks in an active-document record, tolerating old shapes."""
    if not meta:
        return 0
    chunks = meta.get("chunks")
    if isinstance(chunks, list):
        return len(chunks)
    if isinstance(chunks, int):
        return chunks
    return int(meta.get("chunk_count") or 0)


# --------------------------------------------------------------------------- #
# Supporting documents (optional PDFs attached to the active resume)
# --------------------------------------------------------------------------- #
def _attachment_summary(attachment: Dict) -> Dict:
    return {
        "id": attachment.get("id") or attachment.get("filename") or "",
        "filename": attachment.get("filename") or attachment.get("id") or "document",
        "chunks": chunk_count(attachment),
        "uploaded_at": attachment.get("uploaded_at"),
        "size_bytes": attachment.get("size_bytes"),
        "truncated": bool(attachment.get("truncated", False)),
    }


def get_attachments(meta: Optional[Dict] = None) -> List[Dict]:
    """Supporting documents attached to the active resume."""
    if meta is None:
        meta = get_active_doc()
    if not meta:
        return []
    attachments = meta.get("attachments")
    return attachments if isinstance(attachments, list) else []


def attachment_summaries(meta: Optional[Dict] = None) -> List[Dict]:
    return [_attachment_summary(a) for a in get_attachments(meta)]


def add_attachment(attachment: Dict) -> Dict:
    """Append one supporting document to the active resume record."""
    meta = get_active_doc()
    if not meta:
        raise ValueError("No active resume")
    attachments = meta.get("attachments")
    if not isinstance(attachments, list):
        attachments = []
    attachments.append(attachment)
    meta["attachments"] = attachments
    set_active_doc(meta)
    return meta


def remove_attachment(attachment_id: str) -> bool:
    """Remove a supporting document by id. Returns True when it existed."""
    meta = get_active_doc()
    if not meta:
        return False
    attachments = meta.get("attachments")
    if not isinstance(attachments, list):
        return False
    remaining = [a for a in attachments if a.get("id") != attachment_id]
    if len(remaining) == len(attachments):
        return False
    meta["attachments"] = remaining
    set_active_doc(meta)
    return True


def active_resume_status() -> Dict:
    """Summary shared by the status endpoint and the HTML pages."""
    meta = get_active_doc()
    if not meta:
        return {
            "has_resume": False,
            "doc_id": None,
            "filename": None,
            "chunks": 0,
            "uploaded_at": None,
            "indexed": False,
            "attachments": [],
            "attachment_count": 0,
        }
    attachments = attachment_summaries(meta)
    return {
        "has_resume": True,
        "doc_id": meta.get("doc_id"),
        "filename": meta.get("filename") or meta.get("doc_id"),
        "chunks": chunk_count(meta),
        "uploaded_at": meta.get("uploaded_at"),
        "indexed": bool(meta.get("indexed", True)),
        "attachments": attachments,
        "attachment_count": len(attachments),
    }


def get_document_chunks(doc_id: str) -> List[dict]:
    """Chunks of the active document, ordered by chunk_index."""
    meta = get_active_doc()
    if not meta or meta.get("doc_id") != doc_id:
        return []
    chunks = meta.get("chunks")
    if not isinstance(chunks, list):
        return []
    return [
        {
            "doc_id": doc_id,
            "chunk_index": i,
            "page": c.get("page"),
            "text": c.get("text", ""),
        }
        for i, c in enumerate(chunks)
    ]


# --------------------------------------------------------------------------- #
# Sessions (Upstash backend; the local backend lives in sessions/store.py)
# --------------------------------------------------------------------------- #
def kv_create_session() -> str:
    sid = str(uuid.uuid4())
    session = {
        "id": sid,
        "created_at": datetime.utcnow().isoformat(),
        "messages": [],
    }
    _kv_set(_SESSION_PREFIX + sid, session)
    _redis("SADD", _SESSION_INDEX, sid)
    return sid


def kv_get_session(session_id: str) -> Optional[dict]:
    return _kv_get(_SESSION_PREFIX + session_id)


def kv_add_message(session_id: str, role: str, content: str) -> None:
    session = kv_get_session(session_id)
    if not session:
        return
    session.setdefault("messages", []).append({"role": role, "content": content})
    _kv_set(_SESSION_PREFIX + session_id, session)


def kv_list_sessions() -> List[dict]:
    ids = _redis("SMEMBERS", _SESSION_INDEX) or []
    sessions = []
    for sid in ids:
        session = kv_get_session(sid)
        if not session:
            continue
        title = next(
            (m.get("content") for m in session.get("messages", []) if m.get("role") == "user"),
            None,
        )
        sessions.append(
            {
                "id": session.get("id", sid),
                "created_at": session.get("created_at"),
                "title": title,
            }
        )
    sessions.sort(key=lambda s: s.get("created_at") or "", reverse=True)
    return sessions


def kv_delete_session(session_id: str) -> bool:
    existed = kv_get_session(session_id) is not None
    _redis("DEL", _SESSION_PREFIX + session_id)
    _redis("SREM", _SESSION_INDEX, session_id)
    return existed
