#!/bin/bash
set -e
echo "Starting Course RAG Chatbot on port 7860..."
cd /app/backend
exec uv run uvicorn app:app --host 0.0.0.0 --port 7860 --workers 1
