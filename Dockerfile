# Backend image for Resume Coach (FastAPI + local JSON/SQLite state).
# Fallback host for Railway / Render / Fly.io. On Vercel the backend runs as a
# Vercel Service (see vercel.json) — this image is not required there.
#
#   docker build -t resume-coach-api .
#   docker run -p 8000:8000 \
#     -e LLM_PROVIDER=gemini \
#     -e GEMINI_API_KEY=your_key \
#     -e FRONTEND_URL=https://your-app.vercel.app \
#     -v resume_data:/data \
#     resume-coach-api
#
# /data holds the active resume JSON and sessions.db. Mount a persistent volume
# there or uploads vanish on redeploy.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/data \
    SESSIONS_DB_PATH=/data/sessions.db \
    BACKEND_PORT=8000

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend ./backend

RUN useradd --create-home appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /data /app
USER appuser

EXPOSE 8000

# Railway/Render/Fly inject $PORT; default to 8000.
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
