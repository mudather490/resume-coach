from pypdf import PdfReader
from typing import List, Dict, Optional

def extract_pdf_pages(file_path: str) -> List[Dict]:
    reader = PdfReader(file_path)
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append({"page": i, "text": text})
    return pages

def chunk_text(text: str, size: int = 500, overlap: int = 50) -> List[str]:
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
        if start < 0:
            start = 0
    return chunks

def chunk_pages(pages: List[Dict], size: int = 500, overlap: int = 50) -> List[Dict]:
    result = []
    for page in pages:
        for chunk in chunk_text(page["text"], size, overlap):
            result.append({"text": chunk, "page": page["page"]})
    return result
