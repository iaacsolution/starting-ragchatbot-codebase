from unittest.mock import MagicMock
from fastapi.testclient import TestClient

# --- /api/query ---


def test_query_creates_session_when_none_provided(
    client: TestClient, mock_rag: MagicMock
):
    response = client.post("/api/query", json={"query": "What is RAG?"})

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Test answer"
    assert data["sources"] == ["Python Basics - Lesson 1"]
    assert data["session_id"] == "session_1"
    mock_rag.session_manager.create_session.assert_called_once()


def test_query_reuses_provided_session(client: TestClient, mock_rag: MagicMock):
    response = client.post(
        "/api/query",
        json={"query": "What is RAG?", "session_id": "existing_session"},
    )

    assert response.status_code == 200
    assert response.json()["session_id"] == "existing_session"
    mock_rag.session_manager.create_session.assert_not_called()
    mock_rag.query.assert_called_once_with("What is RAG?", "existing_session")


def test_query_returns_500_on_rag_error(client: TestClient, mock_rag: MagicMock):
    mock_rag.query.side_effect = Exception("RAG pipeline failure")

    response = client.post("/api/query", json={"query": "crash"})

    assert response.status_code == 500
    assert "RAG pipeline failure" in response.json()["detail"]


def test_query_requires_query_field(client: TestClient):
    response = client.post("/api/query", json={})

    assert response.status_code == 422


# --- /api/courses ---


def test_courses_returns_catalog_stats(client: TestClient):
    response = client.get("/api/courses")

    assert response.status_code == 200
    data = response.json()
    assert data["total_courses"] == 2
    assert "Python Basics" in data["course_titles"]
    assert "Advanced RAG" in data["course_titles"]


def test_courses_returns_500_on_error(client: TestClient, mock_rag: MagicMock):
    mock_rag.get_course_analytics.side_effect = Exception("DB unavailable")

    response = client.get("/api/courses")

    assert response.status_code == 500
    assert "DB unavailable" in response.json()["detail"]
