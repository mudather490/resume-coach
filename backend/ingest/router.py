import os
import tempfile
import time
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException

from backend.config import CHUNK_SIZE, CHUNK_OVERLAP, MAX_UPLOAD_MB
from backend.ingest.pdf_parser import extract_pdf_pages, chunk_pages
from backend.db.store import (
    clear_active_doc,
    set_active_doc,
    get_active_doc,
)
from backend.models.schemas import IngestResponse, IngestStatus
from backend.resume.prompts import UPLOAD_REJECTION
from backend.resume.guardrails import is_resume_document_fast

router = APIRouter()


def _chunk_count(meta: dict) -> int:
    chunks = meta.get("chunks")
    if isinstance(chunks, list):
        return len(chunks)
    if isinstance(chunks, int):
        return chunks
    return int(meta.get("chunk_count") or 0)


@router.post("", response_model=IngestResponse)
async def ingest_pdf(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty")
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"PDF is too large (max {MAX_UPLOAD_MB} MB)")

    doc_id = os.path.basename(file.filename)
    started = time.perf_counter()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        pages = extract_pdf_pages(tmp_path)
        full_text = "\n".join(page["text"] for page in pages).strip()
        if not full_text:
            raise HTTPException(status_code=400, detail="No text extracted from PDF")

        # Fast heuristic gate: no LLM call on the upload hot path.
        if not is_resume_document_fast(full_text):
            raise HTTPException(status_code=400, detail=UPLOAD_REJECTION)

        chunks = chunk_pages(pages, CHUNK_SIZE, CHUNK_OVERLAP)
        if not chunks:
            raise HTTPException(status_code=400, detail="No text extracted from PDF")

        # The chunk text is stored inside the active-document metadata: chat
        # sends the whole resume as context, so a separate vector index (and
        # the embeddings it needs) is not required. This also keeps uploads
        # fast and works inside a stateless serverless function.
        meta = {
            "doc_id": doc_id,
            "filename": doc_id,
            "chunk_count": len(chunks),
            "chunks": [{"text": c["text"], "page": c["page"]} for c in chunks],
            "uploaded_at": datetime.utcnow().isoformat(),
            "indexed": True,
        }
        set_active_doc(meta)

        elapsed = time.perf_counter() - started
        print(f"[ingest] {doc_id}: saved {len(chunks)} chunks in {elapsed:.2f}s")
        return IngestResponse(doc_id=doc_id, filename=doc_id, chunks=len(chunks))
    finally:
        os.unlink(tmp_path)


@router.get("/status", response_model=IngestStatus)
def ingest_status():
    meta = get_active_doc()
    if not meta:
        return IngestStatus(has_resume=False)
    return IngestStatus(
        has_resume=True,
        doc_id=meta.get("doc_id"),
        filename=meta.get("filename") or meta.get("doc_id"),
        chunks=_chunk_count(meta),
        uploaded_at=meta.get("uploaded_at"),
        indexed=bool(meta.get("indexed", True)),
    )


@router.delete("/reset")
def reset_index():
    """Clear the active resume."""
    meta = get_active_doc()
    deleted = _chunk_count(meta) if meta else 0
    clear_active_doc()
    return {"ok": True, "deleted_chunks": deleted}
