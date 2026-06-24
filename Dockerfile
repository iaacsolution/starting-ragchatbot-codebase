FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY docs/ ./docs/

RUN mkdir -p backend/chroma_db

# Pre-index courses at build time (sentence-transformers only, no API key needed)
RUN cd /app/backend && uv run python -c "\
from vector_store import VectorStore; \
from config import config; \
vs = VectorStore(config); \
vs.add_course_folder('../docs'); \
print('Pre-indexing complete')"

COPY entrypoint_hf.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 7860

ENTRYPOINT ["/entrypoint.sh"]
