import chromadb
from typing import List, Optional, Dict
from backend.config import CHROMA_PATH, CHROMA_COLLECTION

_client = None
_collection = None

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
