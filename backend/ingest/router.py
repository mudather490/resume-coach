from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.config import CHUNK_SIZE, CHUNK_OVERLAP
from backend.ingest.pdf_parser import extract_pdf_pages, chunk_pages
from backend.llm import embed
from backend.db.chroma_client import upsert_chunks
from backend.models.schemas import IngestResponse
from backend.resume.prompts import UPLOAD_REJECTION
from backend.resume.guardrails import is_resume_document
import tempfile, os

router = APIRouter()

@router.post("", response_model=IngestResponse)
async def ingest_pdf(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    doc_id = file.filename
    suffix = ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        pages = extract_pdf_pages(tmp_path)
        full_text = "\n".join(page["text"] for page in pages).strip()
        if not full_text:
            raise HTTPException(status_code=400, detail="No text extracted from PDF")

        if not is_resume_document(full_text):
            raise HTTPException(status_code=400, detail=UPLOAD_REJECTION)

        chunks = chunk_pages(pages, CHUNK_SIZE, CHUNK_OVERLAP)
        if not chunks:
            raise HTTPException(status_code=400, detail="No text extracted from PDF")

        texts = [c["text"] for c in chunks]
        embeddings = embed(texts)
        upsert_chunks(doc_id, chunks, embeddings)
        return IngestResponse(doc_id=doc_id, chunks=len(chunks))
    finally:
        os.unlink(tmp_path)
