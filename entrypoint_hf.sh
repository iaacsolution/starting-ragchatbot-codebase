#!/bin/bash
set -e
echo "Indexing courses..."
cd /app/backend
uv run python -c "
from rag_system import RAGSystem
from config import config
RAGSystem(config)
print('Indexing complete')
"
echo "Starting Course RAG Chatbot on port 7860..."
exec uv run uvicorn app:app --host 0.0.0.0 --port 7860 --workers 1
