---
name: Run Dev Server
description: Start the Course RAG system development server with proper setup
type: skill
---

# Run Dev Server Skill

Automates starting the Course Materials RAG application with validation.

## Usage
When a user asks to "start the app", "run the server", "start development", invoke this skill.

## Validation Steps
1. **Check prerequisites**:
   - Verify `.env` file exists in project root
   - Check `ANTHROPIC_API_KEY` is set
   - Verify Python 3.13+ installed via `python --version`

2. **Install dependencies** (if needed):
   ```bash
   uv sync
   ```

3. **Start server**:
   ```bash
   cd backend && uv run uvicorn app:app --reload --port 8000
   ```

## Success Indicators
- Server logs show: `INFO:     Uvicorn running on http://127.0.0.1:8000`
- API docs accessible at `http://localhost:8000/docs`
- Console output shows: `Loaded X courses with Y chunks`

## Troubleshooting
- **No documents loaded**: Check `docs/` folder exists and contains .txt files
- **Module not found errors**: Ensure running from `backend/` directory
- **API key missing**: Create `.env` with `ANTHROPIC_API_KEY=your_key`
- **Port 8000 in use**: Kill existing process or use `--port 8001`

## Post-Startup
After server is running:
- Open browser to `http://localhost:8000`
- Verify course stats appear in sidebar
- Try a suggested question to test full flow
