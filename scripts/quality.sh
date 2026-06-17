#!/usr/bin/env bash
# Run all code quality checks from the project root.
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Formatting with black ==="
python -m black backend/

echo ""
echo "=== Running tests ==="
python -m pytest backend/tests/ -v

echo ""
echo "Quality checks passed."
