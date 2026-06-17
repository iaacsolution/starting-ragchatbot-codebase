import sys
import os

# Make backend package importable without installing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import List, Optional


# ---------------------------------------------------------------------------
# Test app — mirrors app.py routes without the static-file mount, which
# requires a ../frontend directory that does not exist in CI / test runs.
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    session_id: str

class CourseStats(BaseModel):
    total_courses: int
    course_titles: List[str]


def create_test_app(rag_system) -> FastAPI:
    """Build a minimal FastAPI app that mirrors the real endpoints."""
    app = FastAPI(title="RAG System — Test")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root():
        return {"status": "ok"}

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()
            answer, sources = rag_system.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_rag_system():
    """RAGSystem mock with sensible defaults for all test cases."""
    mock = MagicMock()
    mock.session_manager.create_session.return_value = "session_1"
    mock.query.return_value = ("Test answer about RAG.", ["Python Basics - Lesson 1"])
    mock.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Python Basics", "Advanced RAG"],
    }
    return mock


@pytest.fixture
def client(mock_rag_system):
    """Starlette TestClient wired to the test app."""
    app = create_test_app(mock_rag_system)
    return TestClient(app)


# ---------------------------------------------------------------------------
# Reusable test-data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def query_payload():
    return {"query": "What is retrieval-augmented generation?"}


@pytest.fixture
def query_payload_with_session():
    return {"query": "What is retrieval-augmented generation?", "session_id": "existing_session"}


@pytest.fixture
def sample_courses():
    return {
        "total_courses": 3,
        "course_titles": ["Python Basics", "Advanced RAG", "LLM Fine-Tuning"],
    }
