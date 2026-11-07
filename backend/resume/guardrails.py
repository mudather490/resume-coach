"""Scope guards for the resume chatbot.

Three layers, cheapest first:
1. Keyword input screens in pure Python (no model call) for obvious cases.
2. A tiny single-letter LLM classifier for ambiguous messages/documents.
3. Enforcement in the coach system prompt (see prompts.py).

Research note: prompt-only restrictions fail unpredictably; the Python screen
runs BEFORE any model call so off-topic requests cost nothing at all.
"""

import re
from backend.llm import chat as llm_chat

ALLOW_RE = re.compile(
    r"\b("
    r"resume|r[eé]sum[eé]|cv\b|curriculum\s+vitae|cover\s+letter"
    r"|job\s+(?:hunt|search|application|application|posting|openings?|description|post)"
    r"|work\s+(?:experience|history)|professional\s+(?:summary|experience)"
    r"|career\s+summary|summary\s+section|bullet\s*(?:point|s)|achievements?|accomplishments?"
    r"|ats\b|applicant\s+tracking|hiring|recruiter|recruitment|head[- ]?hunter"
    r"|internship|work\s+position|employers?|job\s+titles?"
    r"|(?:skills?|experience|education|summary)\s+(?:section|part|\blist\b)"
    r"|one\s*[-\s]?page|ats[- ]friendly|linkedin\s+profile|employment\s+(?:gap|history)"
    r"|supporting\s+(?:document|doc|file|pdf)s?"
    r"|attachments?"
    r"|project\s+(?:file|doc|document|pdf|notes?)"
    r"|portfolio|certificates?|projects?"
    r")\b",
    re.I,
)

SELF_FACT_RE = re.compile(
    r"\b(?:my|i|i'm|i\s+am)\b.{0,60}\b("
    r"gpa|grades?|degree|education|school|university|college|salary|compensation|"
    r"experience|skills?|strengths?|weaknesses?|name|email|phone|number|address|"
    r"location|linkedin|github|portfolio|employer|company|job|work|worked|title|"
    r"role|position|projects?|certifications?|awards?|languages?|achievements?|"
    r"studied|graduate|graduated"
    r")\b",
    re.I,
)

DENY_RE = re.compile(
    r"\b("
    r"python|javascript|typescript|c\+\+|rust|go\s+code|code|script|program|sdk|api|compile"
    r"|poem|poetry|story|novel|screenplay|essay|homework|assignment|quiz|recipe|riddle|joke"
    r"|math\s+(?:problem|equation)|solve\s+(?:this|the)\s+equation|physics|chemistry"
    r"|translate|weather|stock\s+(?:price|market)|constitution|law\s+of"
    r")\b",
    re.I,
)

CLASSIFIER_PROMPT = """You are the gatekeeper of a resume-writing assistant. Decide if the user's \
latest message is about a resume/CV or the user's own work background (developing, reviewing, \
expanding, shortening, or asking questions about it), based on the recent conversation.

Recent conversation:
{history}

Latest message:
<<<USER>>>
{message}
<<<END>>>

A = resume-related
B = anything else
Reply with exactly one letter."""

INTENT_SHORTEN_RE = re.compile(
    r"\b(shorten|shorter|condense|concise|tighten|tighter|trim|cut\s+down|too\s+long|"
    r"one\s*[-\s]?page|1\s*page|reduce\s+(?:the\s+)?length|boil\s+down|shr[io]nk|less\s+words)\b",
    re.I,
)
INTENT_EXPAND_RE = re.compile(
    r"\b(ex?pand|elaborate|flesh\s+out|enrich|more\s+details?|more\s+descriptive|longer|"
    r"add\s+(?:more\s+)?detail|extend|amplify|develop\s+more|write\s+more|bulk\s+up)\b",
    re.I,
)
INTENT_BUILD_RE = re.compile(
    r"\b(?:build|create|generate|draft|produce|assemble|rebuild)\b.{0,40}\b(?:a\s+)?"
    r"(?:new\s+|fresh\s+|complete\s+|full\s+)?resume\b"
    r"|\bmake\s+(?:me\s+)?(?:a\s+)?(?:new|fresh|complete|full)\s+resume\b"
    r"|\b(?:new|fresh|complete|full)\s+resume\b"
    r"|\bresume\s+from\s+scratch\b"
    r"|\brewrite\s+(?:my\s+)?(?:whole\s+|entire\s+)?resume\b",
    re.I,
)
INTENT_REVIEW_RE = re.compile(
    r"\b(review|feedback|critique|criticize|assess|evaluation?|improve|improvements?|"
    r"suggest(?:ion)?s?|recommend(?:ations?)?|polish|stronger|make\s+(?:it|this)\s+better|"
    r"develop(?:ment)?|upgrade|refine|revise|fix|tailor(?:ing)?|proofread|best\s+practices?|"
    r"make\s+(?:my\s+)?resume\s+better)\b",
    re.I,
)

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")
LINK_RE = re.compile(r"\b(?:linkedin\.com|github\.com)\b", re.I)
EDU_RE = re.compile(
    r"\b(bachelor|master|b\.?s\.?c?\.?|b\.?a\.?|m\.?s\.?c?\.?|m\.?a\.?|m\.?b\.?a|ph\.?d|doctorate|"
    r"diploma|university|college|b\.?tech|m\.?tech|degree|gpa)\b",
    re.I,
)
DATE_RANGE_RE = re.compile(
    r"(?:19|20)\d{2}\s*(?:-|–|—|to)\s*(?:(?:19|20)\d{2}|present)", re.I
)
PAPER_HINTS = (
    r"\babstract\b", r"\bet al\b", r"\bbibliography\b", r"\breferences\b", r"\bdoi\b", r"\bisbn\b",
    r"\bintroduction\b", r"\bmethodolog(?:y|ical)\b",
)
BUSINESS_HINTS = (
    r"\binvoice\b", r"\bsubtotal\b", r"\bamount\s+due\b", r"\bdue\s+date\b", r"\border\s+number\b",
    r"\bshipping\b", r"\bbill\s+to\b", r"\breceipt\b", r"\btax\b",
)

SECTION_HEADINGS = {
    "summary", "professional summary", "executive summary", "summary of qualifications",
    "objective", "career objective", "profile", "about me",
    "work experience", "experience", "professional experience", "employment history",
    "employment", "relevant experience", "internships",
    "education", "academic background", "education and training",
    "skills", "technical skills", "core skills", "key skills", "core competencies",
    "certifications", "licenses", "projects", "selected projects", "publications",
    "awards", "achievements", "honors", "languages", "interests", "hobbies",
    "volunteer experience", "volunteer work", "activities", "leadership", "references",
}

DOC_CLASSIFIER_PROMPT = """Decide whether the following text is a resume or CV.

<<<DOC>>>
{excerpt}
<<<END>>>

A = resume or CV
B = not a resume
Reply with exactly one letter."""

MAX_CLASSIFIER_HISTORY_CHARS = 600
MAX_DOC_EXCERPT_CHARS = 6000
MAX_META_SENTENCES = 4

STRUCTURED_RE = re.compile(r"^\s*(?:[-*•‣]|[0-9]+[.)]|#+|>\s)", re.M)

META_OPENERS_RE = re.compile(
    r"^\s*("
    r"i\s+(?:don'?t|do\s+not)\s+know\b"
    r"|i\s+(?:am\s+not\s+sure|cannot|can'?t)\s+(?:find|determinate|tell)\b"
    r"|the\s+(?:provided|given)?\s*context\b"
    r"|there\s+(?:is|are)\s+no\s+(?:mention|information|details?)\b"
    r"|as\s+an\s+ai\b"
    r"|based\s+on\s+the\s+context\b"
    r")",
    re.I,
)


META_CONTEXT_RE = re.compile(
    r"\b(?:the\s+)?(?:provided|given|supplied)\s+context\b"
    r"|\bcontext\s+(?:does\s+not|doesn'?t|did\s+not|didn'?t)\s+(?:mention|contain|include|provide)\b"
    r"|\b(?:the\s+)?context\s+appears\s+to\s+be\b",
    re.I,
)


def looks_like_meta_answer(answer: str) -> bool:
    """True when the model talks about the context instead of doing the work."""
    return bool(META_CONTEXT_RE.search(answer or ""))


MISSING_FACT_RE = re.compile(
    r"\b(?:is|are|was|were)\s+not\s+(?:mentioned|listed|included|present|provided|specified)\b"
    r"|\b(?:doesn'?t|does\s+not|don'?t|do\s+not)\s+(?:mention|list|include|contain|show|provide|specify)\b"
    r"|\bnot\s+(?:found|present|included)\s+in\s+(?:your|the)\s+resume\b"
    r"|\bno\s+(?:mention|information|details?)\s+(?:of|about|regarding|on)\b"
    r"|\b(?:your|the)\s+resume\s+(?:does\s+not|doesn'?t)\s+(?:mention|list|include|contain|show|provide)\b",
    re.I,
)


def looks_like_missing_fact(answer: str) -> bool:
    """True when the model says the requested fact is absent from the resume."""
    return bool(MISSING_FACT_RE.search(answer or ""))


FACT_QUERY_RE = re.compile(
    r"^\s*(?:what|where|when|who|which|how\s+(?:many|much))\b"
    r"|\b(?:does|do|did)\b.{0,40}\b(?:mention|list|include|contain|show|state|have)\b",
    re.I,
)

FACT_STOPWORDS = {
    "the", "a", "an", "my", "your", "our", "their", "his", "her", "its", "this", "that",
    "these", "those", "is", "are", "was", "were", "be", "been", "being", "do", "does",
    "did", "have", "has", "had", "can", "could", "would", "should", "will", "shall",
    "may", "might", "must", "i", "you", "we", "they", "he", "she", "it", "me", "us",
    "them", "what", "which", "who", "whom", "whose", "when", "where", "why", "how",
    "many", "much", "about", "of", "in", "on", "at", "to", "for", "from", "with",
    "by", "and", "or", "not", "no", "any", "some", "all", "there", "here", "mention",
    "mentions", "mentioning", "list", "lists", "listed", "include", "includes",
    "included", "contain", "contains", "contained", "show", "shows", "shown", "state",
    "states", "stated", "say", "says", "resume", "cv", "page", "pages", "file",
    "document", "uploaded", "provide", "provided", "tell", "please", "can", "get",
    "give", "know", "see", "find", "look", "like", "info", "information", "details",
}

ADVICE_WORDS = {
    "add", "improve", "improvement", "recommend", "recommendation", "tip", "tips",
    "best", "better", "good", "bad", "strong", "weak", "write", "make", "develop",
    "developing", "help", "need", "want", "suggest", "suggestion", "suggestions",
    "advice", "review", "fix", "tailor", "polish", "rewrite", "edit", "change",
    "fit", "qualify", "qualified", "suitable", "ready", "should", "could", "would",
    "improve", "enhance", "optimize", "increase", "reduce", "score", "rate",
}

FIELD_WORDS = {
    "name", "email", "phone", "contact", "address", "location", "linkedin", "github",
    "website", "portfolio", "education", "experience", "skill", "skills", "summary",
    "objective", "project", "projects", "certification", "certifications", "award",
    "awards", "language", "languages", "reference", "references", "work", "job",
    "title", "company", "employer", "role", "degree", "university", "college",
}


def asks_about_missing_fact(message: str, resume_text: str) -> bool:
    """Cheap groundedness check for factual questions.

    When the user asks 'what is my X' / 'does my resume mention X' and none of
    the meaningful words appear in the resume, answer 'not in this resume'
    immediately instead of paying for a slow, unreliable LLM round-trip.
    """
    if not FACT_QUERY_RE.search(message):
        return False
    tokens = re.findall(r"[a-z][a-z0-9+#.]{2,}", message.lower())
    meaningful = [
        t for t in tokens
        if t not in FACT_STOPWORDS and t not in ADVICE_WORDS
    ]
    if not meaningful:
        return False
    text = (resume_text or "").lower()
    for token in meaningful:
        if token in FIELD_WORDS:
            return False
        if re.search(r"(?<![a-z0-9])" + re.escape(token) + r"(?![a-z0-9])", text):
            return False
    return True


def strip_dismissive_preamble(answer: str) -> str:
    """Layer-3 reply screen: drop meta sentences like 'I don't know. The provided
    context...' so the reply opens with the actual work instead (see the
    ResumeAI-style research note: a reply screen catches what the prompt is
    talked past). Only plain prose is touched; bullet/heading replies are kept."""
    text = answer.strip()
    if not text:
        return text

    if META_CONTEXT_RE.search(text):
        sentences = re.split(r"(?<=[.!?])\s+", text)
        text = " ".join(s for s in sentences if not META_CONTEXT_RE.search(s)).strip()
        if not text:
            return text

    if STRUCTURED_RE.search(text[:80]):
        return text
    for _ in range(MAX_META_SENTENCES):
        m = re.search(r"\s*(.{1,260}?[.!?])(\s+|$)", text, re.S)
        if not m or not META_OPENERS_RE.search(m.group(1)):
            break
        text = text[m.end():].strip()
        if not text or STRUCTURED_RE.search(text[:80]):
            break
    return text


def sanitize_for_fence(text: str) -> str:
    """Stop user text from breaking out of the <<< >>> fences."""
    return text.replace("<<<", "‹‹‹").replace(">>>", "›››").replace("```", "ThreeBackticks")


def is_resume_related(message: str, history: list | None = None) -> bool:
    """Layer-1 keyword screens, layer-2 single-letter LLM classifier."""
    text = message.lower()
    if ALLOW_RE.search(text):
        return True
    if SELF_FACT_RE.search(text):
        return True
    if DENY_RE.search(text):
        return False

    history_lines = []
    for m in (history or [])[-3:]:
        snippet = m["content"][:150]
        history_lines.append(f"{m['role']}: {snippet}")
    history_block = "\n".join(history_lines)[:MAX_CLASSIFIER_HISTORY_CHARS] or "(empty)"

    prompt = CLASSIFIER_PROMPT.format(history=history_block, message=sanitize_for_fence(message))
    try:
        out = llm_chat([{"role": "user", "content": prompt}], temperature=0.0)
    except Exception:
        return True
    letter = (out or "").strip().upper()[:1]
    if letter == "A":
        return True
    if letter == "B":
        return False
    return True


def classify_intent(message: str) -> str:
    """review | expand | shorten | build | general — matches the coach's services."""
    text = message
    if INTENT_SHORTEN_RE.search(text):
        return "shorten"
    if INTENT_EXPAND_RE.search(text):
        return "expand"
    if INTENT_BUILD_RE.search(text):
        return "build"
    if INTENT_REVIEW_RE.search(text):
        return "review"
    return "general"


def _heuristic_resume_score(text: str) -> int:
    lines = [line for line in text.splitlines() if line.strip()]
    headings = sum(1 for line in lines[:70] if _is_heading_line(line))
    contact = 0
    if EMAIL_RE.search(text):
        contact += 1
    if PHONE_RE.search(text):
        contact += 1
    if LINK_RE.search(text):
        contact += 1
    contact = min(contact, 2)
    edu = 1 if EDU_RE.search(text) else 0
    dates = 1 if len(DATE_RANGE_RE.findall(text)) >= 1 else 0
    bullets = 1 if sum(1 for line in lines if line.lstrip()[:1] in {"•", "‣", "-", "*", "‒",
                                                                    "–", "—"}) >= 3 else 0
    paper = sum(1 for hint in PAPER_HINTS if re.search(hint, text, re.I))
    business = sum(1 for hint in BUSINESS_HINTS if re.search(hint, text, re.I))
    score = headings * 2 + contact + edu + dates + bullets
    score -= min(paper + business, 3) * 2
    return score


def _is_heading_line(line: str) -> bool:
    cleaned = re.sub(r"[^a-z ]+", "", line.strip().lower()).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned in SECTION_HEADINGS


def is_resume_document_fast(text: str) -> bool:
    """Fast upload gate: heuristics only, so uploads stay under a few seconds.

    A score of 3+ is a confident resume; 0-1 is confidently not a resume. The
    ambiguous middle (2) is accepted only when there is concrete contact/date
    evidence, which keeps false accepts low without calling the LLM.
    """
    score = _heuristic_resume_score(text)
    if score >= 3:
        return True
    if score <= 1:
        return False
    return bool(
        EMAIL_RE.search(text)
        or PHONE_RE.search(text)
        or len(DATE_RANGE_RE.findall(text)) >= 2
    )


def is_resume_document(text: str) -> bool:
    """Decide whether extracted PDF text is a resume/CV (upload gate)."""
    score = _heuristic_resume_score(text)
    if score >= 4:
        return True
    if score <= 0:
        return False
    prompt = DOC_CLASSIFIER_PROMPT.format(excerpt=sanitize_for_fence(text[:MAX_DOC_EXCERPT_CHARS]))
    try:
        out = llm_chat([{"role": "user", "content": prompt}], temperature=0.0)
    except Exception:
        return score >= 2
    letter = (out or "").strip().upper()[:1]
    if letter == "A":
        return True
    if letter == "B":
        return False
    return score >= 2
