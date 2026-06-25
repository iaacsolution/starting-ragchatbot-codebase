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

# Pre-download embedding model and pre-index all courses at build time.
# This bakes the ChromaDB directly into the image so startup is instant
# and retrieval is guaranteed correct regardless of runtime environment.
RUN uv run python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2'); print('Model cached.')"
RUN uv run python backend/preindex.py

COPY entrypoint_hf.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 7860

ENTRYPOINT ["/entrypoint.sh"]
