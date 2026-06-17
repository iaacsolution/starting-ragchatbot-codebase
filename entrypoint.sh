#!/bin/bash
set -e

OLLAMA_MODEL=${OLLAMA_MODEL:-llama2}
OLLAMA_URL=${OLLAMA_API_URL:-http://ollama:11434}

echo "Waiting for Ollama at ${OLLAMA_URL}..."
until curl -sf "${OLLAMA_URL}/api/version" > /dev/null 2>&1; do
  sleep 3
done
echo "Ollama is ready."

echo "Pulling model: ${OLLAMA_MODEL} (skipped if already cached)..."
curl -s -X POST "${OLLAMA_URL}/api/pull" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"${OLLAMA_MODEL}\"}" | grep -E '"status"' | tail -1

echo "Starting application..."
cd /app/backend
exec uv run uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1
