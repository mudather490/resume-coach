"""HTML pages for the single-process FastAPI app."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from backend.config import MAX_UPLOAD_MB
from backend.db.store import active_resume_status
from backend.sessions.store import list_sessions
from backend.web.markdown import markdown_to_plain_text, render_markdown

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.filters["markdown"] = render_markdown
templates.env.filters["plain"] = markdown_to_plain_text

router = APIRouter(include_in_schema=False)


def _context(request: Request, page: str, **extra) -> dict:
    return {
        "page": page,
        "max_upload_mb": MAX_UPLOAD_MB,
        **extra,
    }


@router.get("/", response_class=HTMLResponse)
def home_page(request: Request):
    return templates.TemplateResponse(request, "index.html", _context(request, "home"))


@router.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse(
        request,
        "upload.html",
        _context(request, "upload", resume=active_resume_status()),
    )


@router.get("/chat", response_class=HTMLResponse)
def chat_page(request: Request):
    return templates.TemplateResponse(
        request,
        "chat.html",
        _context(
            request,
            "chat",
            resume=active_resume_status(),
            sessions=list_sessions(),
        ),
    )
