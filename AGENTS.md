# AI Agent Instructions - Course Materials RAG System

## Contexte Métier

Ce système est un **assistant pédagogique RAG** destiné à des apprenants en ingénierie IA. Il répond à des questions sur 4 cours DeepLearning.ai :

| Cours | Thème |
|-------|-------|
| course1_script.txt | Building Towards Computer Use with Anthropic |
| course2_script.txt | MCP: Build Rich-Context AI Apps with Anthropic |
| course3_script.txt | Advanced Retrieval for AI with Chroma |
| course4_script.txt | Prompt Compression and Query Optimization |

**Règles métier fondamentales :**
- Réponses courtes, sourcées, factuelles — jamais d'invention hors corpus
- Mono-domaine : si la question dépasse les cours chargés, le dire clairement
- Latence acceptable : l'inférence Ollama locale peut prendre 10–30 s

---

This is a **Retrieval-Augmented Generation (RAG) system** for answering questions about course materials using semantic search and local LLM inference with **Ollama**.

## Quick Start for Agents

### Mode développement local

**Prérequis :**
- Ollama installé et en cours d'exécution (`ollama serve` dans un terminal séparé)
- Modèle llama2 disponible (`ollama pull llama2`)
- Voir `.claude/skills/setup-ollama.md` pour la configuration Ollama

```bash
uv sync
cp .env.example .env
ollama serve                     # terminal séparé
./run.sh
# ou manuellement : cd backend && uv run uvicorn app:app --reload --port 8000
```

### Mode production (Docker)

```bash
# Définir le modèle Ollama si différent de llama2
echo "OLLAMA_MODEL=llama2" > .env

docker compose up --build        # premier lancement (télécharge le modèle ~4 Go)
docker compose up                # lancements suivants
```

L'app est disponible sur `http://localhost:8000`, docs API sur `/docs`.

**Volumes Docker persistants :**
- `chroma_data` → données ChromaDB (ne pas supprimer sans backup)
- `ollama_data` → poids du modèle Ollama mis en cache

## Architecture Overview

### Stack
- **Backend**: FastAPI + uvicorn (Python 3.13)
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Vector Store**: ChromaDB 1.0.15 (local persistence at `./chroma_db`)
- **LLM Engine**: Ollama with llama2 (local inference)
- **Embeddings**: Sentence Transformers (`all-MiniLM-L6-v2`)

### Core Components

| Module | Purpose |
|--------|---------|
| `RAGSystem` (rag_system.py) | Main orchestrator coordinating all components |
| `VectorStore` (vector_store.py) | ChromaDB wrapper for semantic search |
| `OllamaGenerator` (ollama_generator.py) | Ollama API integration for response generation |
| `DocumentProcessor` (document_processor.py) | Chunks documents (800 chars, 100 char overlap) |
| `SessionManager` (session_manager.py) | Tracks conversation history (max 2 messages) |
| `SearchTools` (search_tools.py) | Semantic search tool registration |

### Data Flow

```
User Query (Frontend)
    ↓
POST /api/query (FastAPI)
    ↓
RAGSystem.query()
    ↓
VectorStore.search() [ChromaDB semantic search]
    ↓
OllamaGenerator.generate() [Ollama with search context]
    ↓
QueryResponse (answer + sources)
```

### Key Configuration (backend/config.py)

- **OLLAMA_API_URL**: `http://localhost:11434` (Ollama server location)
- **OLLAMA_MODEL**: `llama2` (Model to use for generation)
- **CHUNK_SIZE**: 800 characters per document chunk
- **CHUNK_OVERLAP**: 100 characters between chunks
- **MAX_RESULTS**: 5 search results returned to Ollama
- **MAX_HISTORY**: 2 messages stored per session
- **CHROMA_PATH**: `./chroma_db` (local storage)
- **EMBEDDING_MODEL**: `all-MiniLM-L6-v2`

## API Endpoints

### POST `/api/query`
Process a user question and return AI-generated answer with sources.

**Request**: `{ "query": string, "session_id": string (optional) }`  
**Response**: `{ "answer": string, "sources": [strings], "session_id": string }`

### GET `/api/courses`
Get loaded course statistics.

**Response**: `{ "total_courses": int, "course_titles": [strings] }`

### GET `/` 
Serves frontend HTML (static file at `/frontend/index.html`)

## Key Files & Patterns

### Backend Structure
```
backend/
├── app.py              # FastAPI app, endpoints, middleware
├── rag_system.py       # Orchestrator - process documents, handle queries
├── vector_store.py     # ChromaDB operations (add/search)
├── ollama_generator.py # Ollama API calls and tool handling
├── document_processor.py # Parse & chunk documents
├── session_manager.py  # Session ID tracking
├── search_tools.py     # Tool manager for Ollama
├── models.py           # Pydantic models (Course, Lesson, CourseChunk)
├── config.py           # Config object from .env
└── requirements.txt    # Dependencies (via uv.lock)
```

### Frontend Structure
```
frontend/
├── index.html  # UI with sidebar + chat interface
├── script.js   # API calls, session management, UI updates
└── style.css   # Styling
```

### Data Input
```
docs/
├── course1_script.txt  # Course content (auto-loaded on startup)
├── course2_script.txt
├── course3_script.txt
└── course4_script.txt
```

## Frontend Details

### UI Structure
- **Left Sidebar**: Course stats + suggested questions
- **Main Chat**: Message display + input box
- **Session Management**: Auto-creates session on page load, keeps session ID for multi-turn conversations

### Suggested Questions
Hardcoded in `frontend/index.html` (lines 44-48). Update `data-question` attribute to add new suggestions:
```html
<button class="suggested-item" data-question="Your question here">Button label</button>
```

### API Integration (script.js)
- Uses relative URL `/api` (works behind proxies)
- `sendMessage()`: Calls POST `/api/query` with `{ query, session_id }`
- `loadCourseStats()`: Calls GET `/api/courses` on page load
- Auto-disables input while waiting for response

## Document Format & Processing

### Expected Document Format
- **File format**: Plain text (.txt)
- **Expected location**: `docs/` folder at project root
- **Auto-loading**: Triggered on server startup if files exist

### Document Structure Parsing
`DocumentProcessor` expects course files with structure like:
```
[Course Title]
[Lesson 1]
Content here...
[Lesson 2]  
More content...
```

The processor:
1. Extracts course title from first line
2. Splits content by lesson markers (regex pattern `\[Lesson.*?\]`)
3. Creates `CourseChunk` objects for vector storage
4. Each chunk includes: text content, course name, lesson info, chunk index

### Data Models (models.py)
- **Course**: title, instructor, description
- **Lesson**: title, content, course reference
- **CourseChunk**: text, course_name, lesson_name, chunk_index (for retrieval)

## Development Conventions

### Imports in Backend
- Use **relative imports**: `from config import config` (not absolute)
- Run backend commands from `backend/` directory

### Error Handling
- Wrap API calls in try/except
- Return HTTPException(500) for errors
- Print errors to stdout

### Type Hints
- Always use type hints (Pydantic BaseModel or dataclass)
- Use Optional for nullable fields
- Use List, Dict, Tuple from typing module

### Response Models
- Use Pydantic BaseModel for API responses
- Include descriptive docstrings on models

### Ollama Integration (ollama_generator.py)
- **Temperature**: 0 (deterministic responses)
- **Max tokens**: 800 (equivalent to Claude's max_tokens)
- **Model**: llama2 (configurable in .env via OLLAMA_MODEL)
- **System prompt**: Instructs Ollama to use search tool only for course-specific queries
- **Tool usage**: One search per query maximum (JSON-formatted detection)
- **API URL**: http://localhost:11434 (configurable via OLLAMA_API_URL)
- **Timeout**: 60 seconds (Ollama inference can be slower than Claude)

## Common Tasks with Examples

### Adding a New Endpoint
1. Define Pydantic model in `app.py`:
```python
class SearchRequest(BaseModel):
    query: str
    category: Optional[str] = None

class SearchResponse(BaseModel):
    results: List[str]
    count: int
```

2. Add route with proper error handling:
```python
@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    try:
        results = rag_system.search(request.query, request.category)
        return SearchResponse(results=results, count=len(results))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Modifying Document Processing
- Edit `document_processor.py` to change chunking logic
- Adjust `CHUNK_SIZE` and `CHUNK_OVERLAP` in `config.py`
- Clear `./chroma_db` to rebuild vector store: `rm -rf chroma_db/`
- Restart server to reload documents

### Updating Ollama Behavior
1. Edit `SYSTEM_PROMPT` in `ollama_generator.py` to change instructions
2. Modify `OLLAMA_MODEL` in `.env` to use different model (e.g., `mistral`, `neural-chat`)
3. Adjust `temperature` in `ollama_generator.py` (currently hardcoded to 0) if needed
4. Restart server to apply changes
5. Test with `/api/query` endpoint

### Switching Ollama Models
```bash
# Pull new model
ollama pull mistral

# Update .env
OLLAMA_MODEL=mistral

# Restart server
./run.sh
```

### Adding a Suggested Question
In `frontend/index.html`, add button in `.suggested-items` div:
```html
<button class="suggested-item" data-question="What are the prerequisites?">Prerequisites</button>
```

### Debugging Vector Search
Use ChromaDB directly in Python:
```python
from vector_store import VectorStore
from config import config

vs = VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL)
results = vs.search_content("your query")
print(results.documents)  # See what was found
```

## Potential Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Cannot connect to Ollama" | Ensure `ollama serve` is running in separate terminal; verify `OLLAMA_API_URL` in .env |
| Ollama model not found | Run `ollama pull llama2` to download model (or chosen model) |
| Very slow responses (10+ sec) | First response is slower (model loading); try faster model like `mistral` |
| High memory usage | Ensure 8GB+ RAM available; stop other applications; try smaller model |
| ChromaDB not initialized | Run startup endpoint (happens auto on server start) |
| Slow semantic search | Reduce `MAX_RESULTS` in config; check embedding model |
| Imports fail in backend | Run commands from `backend/` dir; use relative imports |
| Frontend doesn't load | Check `frontend/index.html` path; verify static files mounted |
| Session ID returns same results | Check `MAX_HISTORY` setting; clear session for new context |
| Tool invocation not working | Check system prompt format in `ollama_generator.py`; verify JSON pattern |
| Docker : app démarre avant Ollama | `entrypoint.sh` attend le healthcheck Ollama — attendre 30–60 s |
| Docker : modèle re-téléchargé à chaque restart | Vérifier que le volume `ollama_data` est bien monté dans `docker-compose.yml` |
| Réponse hors-sujet (hors cours) | Vérifier `SYSTEM_PROMPT` dans `ollama_generator.py` — renforcer "answer only from search results" |

## Related Documentation & Skills

- [README.md](README.md): Installation and running instructions
- [.env.example](.env.example): Environment variable template
- [.claude/skills/setup-ollama.md](.claude/skills/setup-ollama.md): Ollama installation guide
- [.claude/skills/run-dev-server.md](.claude/skills/run-dev-server.md): Server startup with validation
- [.claude/skills/load-course-documents.md](.claude/skills/load-course-documents.md): Adding course materials
- [.claude/skills/frontend-modifications.md](.claude/skills/frontend-modifications.md): UI customization
- API docs: Auto-generated at `/docs` when server running
