"""Conversation history.

Local development: SQLite (``sessions.db`` at the repo root by default).
Vercel: Upstash Redis, selected automatically when its REST env vars exist
(Vercel's filesystem is ephemeral).
"""
import os
import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional

from backend.config import SESSIONS_DB_PATH, USE_KV
from backend.db import store as state

DB_PATH = SESSIONS_DB_PATH


def _conn():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        )
    """)
    conn.commit()
    conn.close()


def create_session() -> str:
    if USE_KV:
        return state.kv_create_session()
    init_db()
    sid = str(uuid.uuid4())
    conn = _conn()
    conn.execute("INSERT INTO sessions (id, created_at) VALUES (?, ?)", (sid, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return sid


def add_message(session_id: str, role: str, content: str):
    if USE_KV:
        state.kv_add_message(session_id, role, content)
        return
    init_db()
    conn = _conn()
    conn.execute("INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                 (session_id, role, content, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def get_session(session_id: str) -> Optional[dict]:
    if USE_KV:
        return state.kv_get_session(session_id)
    init_db()
    conn = _conn()
    row = conn.execute("SELECT id, created_at FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not row:
        conn.close()
        return None
    msgs = conn.execute("SELECT role, content FROM messages WHERE session_id = ? ORDER BY id", (session_id,)).fetchall()
    conn.close()
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "messages": [{"role": m["role"], "content": m["content"]} for m in msgs],
    }


def list_sessions() -> List[dict]:
    if USE_KV:
        return state.kv_list_sessions()
    init_db()
    conn = _conn()
    rows = conn.execute(
        """
        SELECT s.id, s.created_at,
            (SELECT content FROM messages
             WHERE session_id = s.id AND role = 'user'
             ORDER BY id ASC LIMIT 1) AS title
        FROM sessions s
        ORDER BY s.created_at DESC
        """
    ).fetchall()
    conn.close()
    return [{"id": r["id"], "created_at": r["created_at"], "title": r["title"]} for r in rows]


def delete_session(session_id: str) -> bool:
    if USE_KV:
        return state.kv_delete_session(session_id)
    init_db()
    conn = _conn()
    row = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not row:
        conn.close()
        return False
    conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
    return True
