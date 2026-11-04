import json
import os
import threading
from datetime import datetime

import chromadb
from typing import List, Optional, Dict
from backend.config import CHROMA_PATH, CHROMA_COLLECTION

_client = None
_collection = None

_ACTIVE_META_PATH = os.path.join(CHROMA_PATH, "active_resume.json")
_meta_lock = threading.Lock()


def get_client():
    global _client, _collection
    if _client is None:
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
        _collection = _client.get_or_create_collection(name=CHROMA_COLLECTION)
    return _client, _collection


def upsert_chunks(doc_id: str, chunks: List[dict], embeddings: List[List[float]]):
    client, collection = get_client()
    ids = []
    metadatas = []
    documents = []
    embeddings_list = []
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        ids.append(f"{doc_id}_{i}")
        metadatas.append({"doc_id": doc_id, "chunk_index": i, "page": chunk.get("page")})
        documents.append(chunk["text"])
        embeddings_list.append(emb)
    collection.upsert(
        ids=ids,
        embeddings=embeddings_list,
        metadatas=metadatas,
        documents=documents,
    )


def clear_collection() -> int:
    """Delete every indexed chunk (used by DELETE /ingest/reset)."""
    client, collection = get_client()
    ids = collection.get()["ids"]
    if ids:
        collection.delete(ids=ids)
    return len(ids)


def set_active_doc(meta: Dict):
    """Persist which resume the coach should use (survives restarts)."""
    with _meta_lock:
        os.makedirs(os.path.dirname(_ACTIVE_META_PATH) or ".", exist_ok=True)
        with open(_ACTIVE_META_PATH, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)


def clear_active_doc():
    with _meta_lock:
        try:
            os.remove(_ACTIVE_META_PATH)
        except FileNotFoundError:
            pass


def _infer_active_doc() -> Optional[Dict]:
    """Adopt a single pre-existing document created before active-doc tracking."""
    _, collection = get_client()
    try:
        data = collection.get(include=["metadatas"])
    except Exception:
        return None
    metadatas = data.get("metadatas") or []
    doc_ids = sorted({m.get("doc_id") for m in metadatas if m.get("doc_id")})
    if len(doc_ids) != 1:
        return None
    doc_id = doc_ids[0]
    chunks = get_document_chunks(doc_id)
    meta = {
        "doc_id": doc_id,
        "filename": doc_id,
        "chunk_count": len(chunks),
        "chunks": [{"text": c["text"], "page": c["page"]} for c in chunks],
        "uploaded_at": datetime.utcnow().isoformat(),
        "indexed": True,
    }
    set_active_doc(meta)
    return meta


def get_active_doc() -> Optional[Dict]:
    """Return active resume metadata, or None when nothing is indexed."""
    with _meta_lock:
        try:
            with open(_ACTIVE_META_PATH, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            meta = None
    if not meta or not meta.get("doc_id"):
        return _infer_active_doc()

    # Newer metadata carries the resume text, so it is usable before the
    # background embedding job finishes.
    if isinstance(meta.get("chunks"), list) and meta["chunks"]:
        return meta

    doc_id = meta["doc_id"]
    _, collection = get_client()
    try:
        existing = collection.get(where={"doc_id": doc_id}, limit=1)
    except Exception:
        return None
    if not existing.get("ids"):
        return _infer_active_doc()

    # Upgrade metadata created before active-doc tracking added inline text.
    if not isinstance(meta.get("chunks"), list):
        chunks = get_document_chunks(doc_id)
        meta["chunk_count"] = len(chunks)
        meta["chunks"] = [{"text": c["text"], "page": c["page"]} for c in chunks]
        meta["indexed"] = True
        set_active_doc(meta)
    return meta


def get_document_chunks(doc_id: str) -> List[dict]:
    """Return every chunk of one document, ordered by chunk_index."""
    _, collection = get_client()
    result = collection.get(where={"doc_id": doc_id}, include=["documents", "metadatas"])
    rows = list(zip(result.get("documents") or [], result.get("metadatas") or []))
    rows.sort(key=lambda row: row[1].get("chunk_index", 0))
    return [
        {
            "doc_id": doc_id,
            "chunk_index": meta.get("chunk_index", i),
            "page": meta.get("page"),
            "text": text,
        }
        for i, (text, meta) in enumerate(rows)
    ]


def search(query_embedding: List[float], top_k: int = 5) -> List[dict]:
    client, collection = get_client()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]
    return [
        {
            "id": f"{m.get('doc_id')}_{i}",
            "score": 1 - d if d is not None else 0.0,
            "doc_id": m.get("doc_id"),
            "page": m.get("page"),
            "text": t,
        }
        for i, (t, m, d) in enumerate(zip(docs, metas, dists))
    ]
