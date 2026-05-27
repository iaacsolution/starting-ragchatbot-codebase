---
name: Course RAG System
description: AI Agent Skills and Instructions for the Course Materials RAG System
type: agent
---

# Course Materials RAG System - Agent Skills & Instructions

This directory contains customizations for AI agents working on the Course Materials Retrieval-Augmented Generation system.

## 🔑 Key Change: Now Using Ollama for Local LLM Inference

The system has been updated to use **Ollama** for AI-powered responses instead of Claude API:
- ✅ Local LLM inference (no API costs)
- ✅ Privacy-focused (data stays local)
- ✅ Offline capable
- ✅ Easy model switching

## Quick Navigation

### 📘 Main Documentation
- **[AGENTS.md](../AGENTS.md)** - Complete project overview, architecture, API reference, and development conventions

### 🛠 Skills (Automated Task Guides)
These skills provide step-by-step guidance for common development tasks:

0. **[setup-ollama.md](skills/setup-ollama.md)** - Install and configure Ollama (START HERE!)
   - Installation steps for Windows/macOS/Linux
   - Model download and verification
   - Troubleshooting common issues

1. **[run-dev-server.md](skills/run-dev-server.md)** - Start the application with proper validation
   - Prerequisites check (Ollama running, dependencies installed)
   - Server startup
   - Verification steps

2. **[load-course-documents.md](skills/load-course-documents.md)** - Add new course materials to the knowledge base
   - Document format requirements
   - Automatic vs manual loading
   - Verification methods

3. **[frontend-modifications.md](skills/frontend-modifications.md)** - Guidelines for web interface updates
   - File structure and key components
   - Common modifications (questions, styling, chat display)
   - Testing and debugging

## Project Structure at a Glance

```
starting-ragchatbot-codebase/
├── AGENTS.md                 # Main agent guide (architecture, API, conventions)
├── .claude/                  # Agent customization folder
│   ├── agents.md            # This file
│   └── skills/              # Task-specific guides
│       ├── setup-ollama.md
│       ├── run-dev-server.md
│       ├── load-course-documents.md
│       └── frontend-modifications.md
├── backend/                 # Python FastAPI application
│   ├── app.py              # Main endpoints
│   ├── rag_system.py       # RAG orchestrator
│   ├── vector_store.py     # ChromaDB integration
│   ├── ollama_generator.py # Ollama API integration
│   └── ... (other modules)
├── frontend/               # Web interface
│   ├── index.html
│   ├── script.js
│   └── style.css
└── docs/                   # Course materials (input data)
    ├── course1_script.txt
    └── ...
```

## Getting Started as an AI Agent

### First Time? (IMPORTANT!)
1. **FIRST**: Follow [setup-ollama.md](skills/setup-ollama.md) to install Ollama and download llama2 model
2. Read **AGENTS.md** for full context
3. Check the appropriate **skill** for your task
4. Follow the validation steps and examples provided

### Common Workflows

**I need to set up the LLM engine first:**
→ Follow [setup-ollama.md](skills/setup-ollama.md) (REQUIRED!)

**I need to start working on this project:**
→ Follow [run-dev-server.md](skills/run-dev-server.md) (after Ollama is running!)

**I need to add or update course materials:**
→ Follow [load-course-documents.md](skills/load-course-documents.md)

**I need to modify the web interface:**
→ Follow [frontend-modifications.md](skills/frontend-modifications.md)

**I need to add a new API endpoint or modify backend logic:**
→ Refer to AGENTS.md "Common Tasks" section for code examples

## Key Points to Remember

✅ **DO:**
- **Start Ollama first**: Run `ollama serve` in a separate terminal before starting the RAG server
- Use relative imports in backend code
- Run backend commands from `backend/` directory
- Always include type hints with Pydantic models
- Test API changes with `/api/docs` endpoint
- Verify documents load on server startup

❌ **DON'T:**
- Forget to start `ollama serve` - server won't connect without it
- Use absolute imports in backend
- Forget to pull the model: `ollama pull llama2` (or chosen model)
- Delete `chroma_db/` without backing up data
- Hardcode configuration values (use config.py)
- Expect fast responses (Ollama is slower than Claude API but runs locally)

## Questions or Issues?

Refer to **AGENTS.md** → "Potential Issues & Solutions" section for troubleshooting tips.
