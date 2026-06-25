import os
import warnings
from pathlib import Path
from typing import List, Optional

warnings.filterwarnings("ignore", message="resource_tracker: There appear to be.*")

import asyncio
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

from config import config
from query_rewriter import rewrite as rewrite_query
from rag_system import RAGSystem
from ragas_evaluator import evaluate_async, last_scores

# Phoenix tracing setup (no-op if Phoenix is unreachable)
try:
    import socket
    import urllib.parse
    from phoenix.otel import register
    from openinference.instrumentation.anthropic import AnthropicInstrumentor

    _phoenix_endpoint = os.getenv("PHOENIX_ENDPOINT", "http://localhost:6006/v1/traces")
    _parsed = urllib.parse.urlparse(_phoenix_endpoint)
    _phoenix_host = _parsed.hostname or "localhost"
    _phoenix_port = _parsed.port or 6006
    with socket.create_connection((_phoenix_host, _phoenix_port), timeout=1.0):
        pass
    _tracer_provider = register(project_name="rag-chatbot", endpoint=_phoenix_endpoint)
    AnthropicInstrumentor().instrument(tracer_provider=_tracer_provider)
except Exception:
    pass

# Initialize FastAPI app
app = FastAPI(title="Course Materials RAG System", root_path="")

# Prometheus metrics on /metrics
Instrumentator().instrument(app).expose(app)

# Add trusted host middleware for proxy
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Enable CORS with proper settings for proxy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Initialize RAG system
rag_system = RAGSystem(config)


# Pydantic models for request/response
class QueryRequest(BaseModel):
    """Request model for course queries"""

    query: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    """Response model for course queries"""

    answer: str
    sources: List[str]
    session_id: str


class CourseStats(BaseModel):
    """Response model for course statistics"""

    total_courses: int
    course_titles: List[str]


# API Endpoints


@app.post("/api/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Process a query and return response with sources"""
    try:
        session_id = request.session_id
        if not session_id:
            session_id = rag_system.session_manager.create_session()

        answer, sources = rag_system.query(request.query, session_id)

        evaluate_async(
            question=request.query,
            answer=answer,
            contexts=rag_system.last_contexts,
            api_key=config.ANTHROPIC_API_KEY,
            model=config.ANTHROPIC_MODEL,
        )
        return QueryResponse(answer=answer, sources=sources, session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test/stream")
async def test_stream():
    async def generate():
        words = [
            "Bonjour",
            " ",
            "voici",
            " ",
            "un",
            " ",
            "test",
            " ",
            "de",
            " ",
            "streaming",
            " ",
            "token",
            " ",
            "par",
            " ",
            "token",
            ".",
        ]
        for word in words:
            yield f"data: {json.dumps({'text': word})}\n\n"
            await asyncio.sleep(0.15)
        yield f"data: {json.dumps({'done': True, 'sources': [], 'session_id': 'test'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/query/stream")
async def query_stream(request: QueryRequest):
    session_id = request.session_id or rag_system.session_manager.create_session()

    async def generate():
        try:
            history = rag_system.session_manager.get_conversation_history(session_id)
            loop = asyncio.get_event_loop()

            # Rewrite query to improve semantic search recall
            course_titles = [
                c["title"] for c in rag_system.vector_store.get_all_courses_metadata()
            ]
            search_query = await loop.run_in_executor(
                None,
                lambda: rewrite_query(
                    request.query, config.ANTHROPIC_API_KEY, course_titles
                ),
            )
            print(f"[SEARCH] original='{request.query}' rewritten='{search_query}'")

            search_results = await loop.run_in_executor(
                None, lambda: rag_system.search_tool.execute(query=search_query)
            )

            # Fallback: if rewriter changed the query and results look empty, retry with original
            if search_query != request.query and (
                not search_results or "No results found" in search_results
            ):
                print(
                    f"[SEARCH] rewritten query yielded no results, retrying with original"
                )
                search_results = await loop.run_in_executor(
                    None,
                    lambda: rag_system.search_tool.execute(query=request.query),
                )
                rag_system.search_tool.last_sources = (
                    rag_system.search_tool.last_sources
                )
            sources = rag_system.search_tool.last_sources[:]
            rag_system.search_tool.last_sources = []
            rag_system.last_contexts = [search_results] if search_results else []

            if search_results and "No results found" not in search_results:
                prompt = (
                    f"Use the following course content to answer the question.\n\n"
                    f"Course content:\n{search_results}\n\n"
                    f"Question: {request.query}\n\n"
                    f"Answer based only on the course content above. "
                    f"If the content does not answer the question, say so."
                )
            else:
                prompt = (
                    f"Answer this question about AI/ML courses: {request.query}\n\n"
                    f"No specific course content was found. Give a brief general answer "
                    f"and suggest the user try a more specific question."
                )

            full_response = ""
            async for chunk in rag_system.ai_generator.generate_stream(
                query=prompt, conversation_history=history
            ):
                full_response += chunk
                yield f"data: {json.dumps({'text': chunk})}\n\n"
                await asyncio.sleep(0)

            rag_system.session_manager.add_exchange(
                session_id, request.query, full_response
            )
            evaluate_async(
                question=request.query,
                answer=full_response,
                contexts=rag_system.last_contexts,
                api_key=config.ANTHROPIC_API_KEY,
                model=config.ANTHROPIC_MODEL,
            )
            yield f"data: {json.dumps({'sources': sources, 'session_id': session_id, 'done': True})}\n\n"
        except Exception as e:
            print(f"[STREAM ERROR] {type(e).__name__}: {e}")
            yield f"data: {json.dumps({'error': str(e), 'done': True, 'sources': [], 'session_id': session_id})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


_FEEDBACK_FILE = Path("../feedback_log.json")


def _load_feedback() -> list:
    if _FEEDBACK_FILE.exists():
        try:
            return json.loads(_FEEDBACK_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_feedback(log: list) -> None:
    try:
        _FEEDBACK_FILE.write_text(
            json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        print(f"[FEEDBACK] save error: {e}")


_feedback_log: list = _load_feedback()


class FeedbackRequest(BaseModel):
    session_id: str
    rating: int  # 1 = thumbs up, -1 = thumbs down
    query: str = ""


@app.post("/api/feedback")
async def post_feedback(request: FeedbackRequest):
    import ragas_evaluator
    import time

    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "session_id": request.session_id,
        "rating": request.rating,
        "query": request.query,
        "faithfulness": ragas_evaluator.last_scores.get("faithfulness"),
    }
    _feedback_log.append(entry)
    _save_feedback(_feedback_log)
    if request.rating < 0:
        print(
            f"[FEEDBACK-] query={request.query!r} faithfulness={entry['faithfulness']}"
        )
    return {"status": "ok"}


@app.get("/api/feedback/summary")
async def get_feedback_summary():
    if not _feedback_log:
        return {
            "total": 0,
            "positive": 0,
            "negative": 0,
            "accept_rate": None,
            "low_quality": [],
        }

    positive = sum(1 for e in _feedback_log if e["rating"] > 0)
    negative = sum(1 for e in _feedback_log if e["rating"] < 0)
    total = len(_feedback_log)
    accept_rate = round(positive / total, 2) if total else None

    # Count low-quality interactions (negative + faithfulness < 0.6) — no query content exposed
    low_quality_count = sum(
        1
        for e in _feedback_log
        if e["rating"] < 0
        and e.get("faithfulness") is not None
        and e["faithfulness"] < 0.6
    )

    return {
        "total": total,
        "positive": positive,
        "negative": negative,
        "accept_rate": accept_rate,
        "low_quality_count": low_quality_count,
    }


@app.get("/api/metrics/ragas")
async def get_ragas_scores():
    """Return the last RAGAS evaluation scores + auto-tune state"""
    import ragas_evaluator

    history = ragas_evaluator._score_history
    avg = round(sum(history) / len(history), 2) if history else None
    return {
        **ragas_evaluator.last_scores,
        "avg_faithfulness": avg,
        "history_size": len(history),
        "max_results": config.MAX_RESULTS,
    }


@app.get("/api/health")
async def health():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    return {
        "status": "ok",
        "anthropic_key_configured": bool(key),
    }


@app.get("/api/courses", response_model=CourseStats)
async def get_course_stats():
    """Get course analytics and statistics"""
    try:
        analytics = rag_system.get_course_analytics()
        return CourseStats(
            total_courses=analytics["total_courses"],
            course_titles=analytics["course_titles"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def startup_event():
    """Load initial documents on startup"""
    if not config.ANTHROPIC_API_KEY:
        print(
            "[WARNING] ANTHROPIC_API_KEY is not set — API calls will fail. Set it as an env var or HF secret."
        )
    print(f"Using Anthropic model: {config.ANTHROPIC_MODEL}")
    docs_path = "../docs"
    if os.path.exists(docs_path):
        print("Loading initial documents...")
        try:
            courses, chunks = rag_system.add_course_folder(
                docs_path, clear_existing=False
            )
            print(f"Loaded {courses} courses with {chunks} chunks")
        except Exception as e:
            print(f"Error loading documents: {e}")


class DevStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if isinstance(response, FileResponse):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


# Serve static files for the frontend
app.mount("/", DevStaticFiles(directory="../frontend", html=True), name="static")
