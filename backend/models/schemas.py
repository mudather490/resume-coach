from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class Chunk(BaseModel):
    text: str
    page: Optional[int] = None
    doc_id: str
    chunk_index: int

class IngestResponse(BaseModel):
    doc_id: str
    filename: str
    chunks: int

class IngestStatus(BaseModel):
    has_resume: bool
    doc_id: Optional[str] = None
    filename: Optional[str] = None
    chunks: int = 0
    uploaded_at: Optional[str] = None
    indexed: bool = False

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    intent: Optional[str] = None  # auto | review | expand | shorten | general

class ChatResponse(BaseModel):
    answer: str
    sources: List[dict]
    session_id: str
    kind: str = "answer"  # answer | refusal | no_resume | not_found

class Session(BaseModel):
    id: str
    messages: List[dict]
    created_at: datetime
