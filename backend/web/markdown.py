"""Markdown rendering for assistant answers.

The UI used to render Markdown in the browser with react-markdown. Now the same
job happens in Python so the pages and the JSON API return ready-to-insert
HTML. Raw HTML in model output is escaped (``html=False``), and markdown-it
only emits safe link protocols.
"""

import re

from markdown_it import MarkdownIt

QUOTE_CHARS = re.compile(r'["\u201C\u201D\u201E\u201F\u00AB\u00BB]')

_md = MarkdownIt("commonmark", {"html": False, "linkify": False})
_md.enable("table")
_md.enable("strikethrough")


def clean_assistant_text(text: str) -> str:
    """Port of the old frontend ``cleanAssistantText`` helper.

    Removes stray quotation marks, normalises line endings and turns
    bold-only lines into section headings so the coach's replies keep the
    same visual structure as before.
    """
    if not text:
        return ""

    out = QUOTE_CHARS.sub("", text)
    out = out.replace("\r\n", "\n").replace("\r", "\n")
    out = re.sub(r"[ \t]+$", "", out, flags=re.M)
    out = re.sub(r"\n{3,}", "\n\n", out)

    out = re.sub(r"^[ \t]*\*\*(.+?)\*\*[ \t]*:?[ \t]*$", r"## \1", out, flags=re.M)
    out = re.sub(r"^[ \t]*__(.+?)__[ \t]*:?[ \t]*$", r"## \1", out, flags=re.M)
    out = re.sub(r"^[ \t]*\*\*(.+?)\*\*[ \t]*:[ \t]*(.+)$", r"## \1\n\2", out, flags=re.M)
    out = re.sub(r"^[ \t]*(Before|After)[ \t]*:", r"**\1:**", out, flags=re.M)

    return out.strip()


def render_markdown(text: str) -> str:
    """Render an assistant message to sanitised HTML."""
    return _md.render(clean_assistant_text(text or ""))


def markdown_to_plain_text(text: str) -> str:
    """Strip Markdown syntax so an answer can be copied or inserted as text."""
    out = clean_assistant_text(text)
    out = re.sub(r"^#{1,6}[ \t]+", "", out, flags=re.M)
    out = re.sub(r"\*\*(.+?)\*\*", r"\1", out)
    out = re.sub(r"__(.+?)__", r"\1", out)
    out = re.sub(r"(^|[^*])\*([^*\n]+)\*", r"\1\2", out)
    out = re.sub(r"`{1,3}([^`]*)`{1,3}", r"\1", out)
    out = re.sub(r"^[ \t]*[-*+][ \t]+", "", out, flags=re.M)
    out = re.sub(r"^[ \t]*\d+[.)][ \t]+", "", out, flags=re.M)
    out = re.sub(r"^[ \t]*>[ \t]?", "", out, flags=re.M)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()
