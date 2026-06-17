"""API endpoint tests for /api/query, /api/courses, and /."""
import pytest


class TestRootEndpoint:
    def test_root_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_json(self, client):
        response = client.get("/")
        assert response.headers["content-type"].startswith("application/json")


class TestQueryEndpoint:
    def test_returns_200_with_valid_payload(self, client, query_payload):
        response = client.post("/api/query", json=query_payload)
        assert response.status_code == 200

    def test_response_shape(self, client, query_payload):
        data = client.post("/api/query", json=query_payload).json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

    def test_creates_session_when_none_provided(self, client, mock_rag_system, query_payload):
        data = client.post("/api/query", json=query_payload).json()
        mock_rag_system.session_manager.create_session.assert_called_once()
        assert data["session_id"] == "session_1"

    def test_uses_provided_session_id(self, client, mock_rag_system, query_payload_with_session):
        data = client.post("/api/query", json=query_payload_with_session).json()
        mock_rag_system.session_manager.create_session.assert_not_called()
        assert data["session_id"] == "existing_session"

    def test_passes_query_and_session_to_rag(self, client, mock_rag_system, query_payload_with_session):
        client.post("/api/query", json=query_payload_with_session)
        mock_rag_system.query.assert_called_once_with(
            query_payload_with_session["query"],
            query_payload_with_session["session_id"],
        )

    def test_answer_and_sources_come_from_rag(self, client, mock_rag_system, query_payload):
        mock_rag_system.query.return_value = ("Custom answer", ["Course X - Lesson 3"])
        data = client.post("/api/query", json=query_payload).json()
        assert data["answer"] == "Custom answer"
        assert data["sources"] == ["Course X - Lesson 3"]

    def test_returns_500_when_rag_raises(self, client, mock_rag_system, query_payload):
        mock_rag_system.query.side_effect = RuntimeError("vector store offline")
        response = client.post("/api/query", json=query_payload)
        assert response.status_code == 500
        assert "vector store offline" in response.json()["detail"]

    def test_returns_422_when_query_field_missing(self, client):
        response = client.post("/api/query", json={})
        assert response.status_code == 422

    def test_returns_422_when_body_is_absent(self, client):
        response = client.post("/api/query")
        assert response.status_code == 422

    def test_accepts_empty_string_query(self, client, query_payload):
        response = client.post("/api/query", json={"query": ""})
        assert response.status_code == 200

    def test_sources_is_list(self, client, query_payload):
        data = client.post("/api/query", json=query_payload).json()
        assert isinstance(data["sources"], list)


class TestCoursesEndpoint:
    def test_returns_200(self, client):
        response = client.get("/api/courses")
        assert response.status_code == 200

    def test_response_shape(self, client):
        data = client.get("/api/courses").json()
        assert "total_courses" in data
        assert "course_titles" in data

    def test_returns_correct_counts(self, client, mock_rag_system):
        data = client.get("/api/courses").json()
        assert data["total_courses"] == 2
        assert data["course_titles"] == ["Python Basics", "Advanced RAG"]

    def test_empty_catalog(self, client, mock_rag_system):
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }
        data = client.get("/api/courses").json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_delegates_to_rag_analytics(self, client, mock_rag_system, sample_courses):
        mock_rag_system.get_course_analytics.return_value = sample_courses
        data = client.get("/api/courses").json()
        assert data["total_courses"] == sample_courses["total_courses"]
        assert data["course_titles"] == sample_courses["course_titles"]

    def test_returns_500_when_rag_raises(self, client, mock_rag_system):
        mock_rag_system.get_course_analytics.side_effect = Exception("chroma connection failed")
        response = client.get("/api/courses")
        assert response.status_code == 500
        assert "chroma connection failed" in response.json()["detail"]

    def test_course_titles_is_list(self, client):
        data = client.get("/api/courses").json()
        assert isinstance(data["course_titles"], list)
