from pydantic import BaseModel, Field
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

class AttachmentInfo(BaseModel):
    id: str
    filename: str
    chunks: int = 0
    uploaded_at: Optional[str] = None
    size_bytes: Optional[int] = None
    truncated: bool = False

class AttachmentResponse(BaseModel):
    id: str
    filename: str
    chunks: int
    attachment_count: int
    truncated: bool = False

class IngestStatus(BaseModel):
    has_resume: bool
    doc_id: Optional[str] = None
    filename: Optional[str] = None
    chunks: int = 0
    uploaded_at: Optional[str] = None
    indexed: bool = False
    attachments: List[AttachmentInfo] = Field(default_factory=list)
    attachment_count: int = 0

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    intent: Optional[str] = None  # auto | review | expand | shorten | general

class ChatResponse(BaseModel):
    answer: str
    # Pre-rendered, sanitised Markdown so the server-rendered UI does not need
    # a JavaScript Markdown library. ``answer`` stays raw for API clients.
    answer_html: Optional[str] = None
    sources: List[dict]
    session_id: str
    kind: str = "answer"  # answer | refusal | no_resume | not_found

class Session(BaseModel):
    id: str
    messages: List[dict]
    created_at: datetime
