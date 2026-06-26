FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Download embedding model BEFORE copying app code so this 470MB layer
# stays cached across backend code changes — only re-downloads when
# pyproject.toml changes (i.e. when packages change).
RUN uv run python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2'); print('Model cached.')"

# courses: v3 — course8 (RAG Production) + course9 (Recherche Information)
COPY docs/ ./docs/
COPY backend/ ./backend/
COPY frontend/ ./frontend/

RUN mkdir -p backend/chroma_db

# Pre-index all courses at build time — bakes ChromaDB into the image.
# Re-runs only when docs/ or backend/ change.
RUN uv run python backend/preindex.py

COPY entrypoint_hf.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 7860

ENTRYPOINT ["/entrypoint.sh"]
