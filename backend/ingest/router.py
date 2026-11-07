import os
import tempfile
import time
import uuid
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException

from backend.config import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    MAX_ATTACHMENTS,
    MAX_ATTACHMENT_TEXT_CHARS,
    MAX_UPLOAD_MB,
)
from backend.ingest.pdf_parser import extract_pdf_pages, chunk_pages, chunk_text
from backend.db.store import (
    active_resume_status,
    add_attachment,
    chunk_count,
    clear_active_doc,
    get_active_doc,
    get_attachments,
    remove_attachment,
    set_active_doc,
)
from backend.models.schemas import (
    AttachmentResponse,
    IngestResponse,
    IngestStatus,
)
from backend.resume.prompts import UPLOAD_REJECTION
from backend.resume.guardrails import is_resume_document_fast

router = APIRouter()


async def _extract_upload(file: UploadFile) -> tuple[list[dict], str, int]:
    """Validate one PDF upload and return its pages, full text and size."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty")
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"PDF is too large (max {MAX_UPLOAD_MB} MB)")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        try:
            pages = extract_pdf_pages(tmp_path)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Could not read this PDF. Try a different file.",
            )
        full_text = "\n".join(page["text"] for page in pages).strip()
        if not full_text:
            raise HTTPException(status_code=400, detail="No text extracted from PDF")
        return pages, full_text, len(content)
    finally:
        os.unlink(tmp_path)


@router.post("", response_model=IngestResponse)
async def ingest_pdf(file: UploadFile = File(...)):
    started = time.perf_counter()
    pages, full_text, _ = await _extract_upload(file)

    # Fast heuristic gate: no LLM call on the upload hot path. Only the primary
    # resume goes through this gate; supporting documents are accepted as-is.
    if not is_resume_document_fast(full_text):
        raise HTTPException(status_code=400, detail=UPLOAD_REJECTION)

    chunks = chunk_pages(pages, CHUNK_SIZE, CHUNK_OVERLAP)
    if not chunks:
        raise HTTPException(status_code=400, detail="No text extracted from PDF")

    doc_id = os.path.basename(file.filename)

    # Replacing the resume keeps the user's supporting documents.
    old = get_active_doc()
    attachments = get_attachments(old)

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
        "attachments": attachments,
    }
    set_active_doc(meta)

    elapsed = time.perf_counter() - started
    print(f"[ingest] {doc_id}: saved {len(chunks)} chunks in {elapsed:.2f}s")
    return IngestResponse(doc_id=doc_id, filename=doc_id, chunks=len(chunks))


@router.post("/attachments", response_model=AttachmentResponse)
async def add_supporting_document(file: UploadFile = File(...)):
    """Add an optional supporting PDF (project notes, portfolio, certificates)."""
    meta = get_active_doc()
    if not meta:
        raise HTTPException(
            status_code=400,
            detail="Upload your resume first, then add supporting documents.",
        )

    attachments = get_attachments(meta)
    if len(attachments) >= MAX_ATTACHMENTS:
        raise HTTPException(
            status_code=400,
            detail=f"You can add up to {MAX_ATTACHMENTS} supporting PDFs.",
        )

    _pages, full_text, size_bytes = await _extract_upload(file)
    truncated = len(full_text) > MAX_ATTACHMENT_TEXT_CHARS
    text = full_text[:MAX_ATTACHMENT_TEXT_CHARS]
    chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
    if not chunks:
        raise HTTPException(status_code=400, detail="No text extracted from PDF")

    attachment = {
        "id": uuid.uuid4().hex,
        "filename": os.path.basename(file.filename),
        "chunk_count": len(chunks),
        "chunks": [{"text": c, "page": None} for c in chunks],
        "uploaded_at": datetime.utcnow().isoformat(),
        "size_bytes": size_bytes,
        "truncated": truncated,
    }
    add_attachment(attachment)

    return AttachmentResponse(
        id=attachment["id"],
        filename=attachment["filename"],
        chunks=len(chunks),
        attachment_count=len(attachments) + 1,
        truncated=truncated,
    )


@router.delete("/attachments/{attachment_id}")
def delete_supporting_document(attachment_id: str):
    if not remove_attachment(attachment_id):
        raise HTTPException(status_code=404, detail="Supporting document not found")
    meta = get_active_doc()
    return {"ok": True, "attachment_count": len(get_attachments(meta))}


@router.get("/status", response_model=IngestStatus)
def ingest_status():
    return IngestStatus(**active_resume_status())


@router.delete("/reset")
def reset_index():
    """Clear the active resume and all supporting documents."""
    meta = get_active_doc()
    deleted_chunks = chunk_count(meta)
    deleted_attachments = len(get_attachments(meta))
    clear_active_doc()
    return {
        "ok": True,
        "deleted_chunks": deleted_chunks,
        "deleted_attachments": deleted_attachments,
    }
