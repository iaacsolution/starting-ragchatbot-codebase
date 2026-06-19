import os
import warnings
from pathlib import Path
from typing import List, Optional

warnings.filterwarnings("ignore", message="resource_tracker: There appear to be.*")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

from config import config
from rag_system import RAGSystem
from ragas_evaluator import evaluate_async

# Phoenix tracing setup (no-op if Phoenix is unreachable)
try:
    from phoenix.otel import register
    from openinference.instrumentation.anthropic import AnthropicInstrumentor

    _phoenix_endpoint = os.getenv("PHOENIX_ENDPOINT", "http://localhost:6006/v1/traces")
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
        # Create session if not provided
        session_id = request.session_id
        if not session_id:
            session_id = rag_system.session_manager.create_session()

        # Process query using RAG system
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
            # Add no-cache headers for development
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


# Serve static files for the frontend
app.mount("/", DevStaticFiles(directory="../frontend", html=True), name="static")
