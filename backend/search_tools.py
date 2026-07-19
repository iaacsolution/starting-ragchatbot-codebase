import logging
import math
from typing import Dict, Any, List, Optional, Tuple
from abc import ABC, abstractmethod
from vector_store import VectorStore, SearchResults

logger = logging.getLogger(__name__)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


class Tool(ABC):
    """Abstract base class for all tools"""

    @abstractmethod
    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Execute the tool with given parameters"""
        pass


class CourseSearchTool(Tool):
    """Tool for searching course content with semantic course name matching"""

    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources = []  # Track sources from last search

    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        return {
            "name": "search_course_content",
            "description": "Search course materials with smart course name matching and lesson filtering",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for in the course content",
                    },
                    "course_name": {
                        "type": "string",
                        "description": "Course title (partial matches work, e.g. 'MCP', 'Introduction')",
                    },
                    "lesson_number": {
                        "type": "integer",
                        "description": "Specific lesson number to search within (e.g. 1, 2, 3)",
                    },
                },
                "required": ["query"],
            },
        }

    def execute(
        self,
        query: str,
        course_name: Optional[str] = None,
        lesson_number: Optional[int] = None,
    ) -> str:
        """
        Execute the search tool with given parameters.

        Args:
            query: What to search for
            course_name: Optional course filter
            lesson_number: Optional lesson filter

        Returns:
            Formatted search results or error message
        """

        # Use the vector store's unified search interface
        results = self.store.search(
            query=query, course_name=course_name, lesson_number=lesson_number
        )

        # Handle errors
        if results.error:
            return results.error

        # Handle empty results
        if results.is_empty():
            filter_info = ""
            if course_name:
                filter_info += f" in course '{course_name}'"
            if lesson_number:
                filter_info += f" in lesson {lesson_number}"
            return f"No relevant content found{filter_info}."

        # Format and return results
        return self._format_results(results)

    def _format_results(self, results: SearchResults) -> str:
        """Format search results with course and lesson context"""
        formatted = []
        sources = []  # Track sources for the UI

        for doc, meta in zip(results.documents, results.metadata):
            course_title = meta.get("course_title", "unknown")
            lesson_num = meta.get("lesson_number")

            # Build context header
            header = f"[{course_title}"
            if lesson_num is not None:
                header += f" - Lesson {lesson_num}"
            header += "]"

            # Track source for the UI
            source = course_title
            if lesson_num is not None:
                source += f" - Lesson {lesson_num}"
            sources.append(source)

            formatted.append(f"{header}\n{doc}")

        # Store sources for retrieval
        self.last_sources = sources

        return "\n\n".join(formatted)


class HybridSearchTool(Tool):
    """Search tool using BM25 + Euclidean similarity + cross-encoder reranking."""

    def __init__(self, vector_store: VectorStore, hybrid_retriever) -> None:
        self.store = vector_store
        self.retriever = hybrid_retriever
        self.last_sources: List[str] = []
        self.last_chunks: List[Dict] = []

    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "name": "search_course_content",
            "description": "Search course materials using hybrid retrieval (BM25 + semantic + reranking)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for in the course content",
                    },
                    "course_name": {
                        "type": "string",
                        "description": "Course title (partial matches work, e.g. 'MCP', 'Introduction')",
                    },
                    "lesson_number": {
                        "type": "integer",
                        "description": "Specific lesson number to search within (e.g. 1, 2, 3)",
                    },
                },
                "required": ["query"],
            },
        }

    def execute(
        self,
        query: str,
        course_name: Optional[str] = None,
        lesson_number: Optional[int] = None,
    ) -> str:
        course_title = None
        if course_name:
            course_title = self.store._resolve_course_name(course_name)
            if not course_title:
                return f"No course found matching '{course_name}'."

        results = self.retriever.search(
            query=query,
            k=self.store.max_results,
            course_title=course_title,
            lesson_number=lesson_number,
        )

        if not results:
            if getattr(self.retriever, "corpus_load_degraded", False):
                logger.error(
                    "HybridSearchTool.execute: corpus_load_degraded=True for "
                    "query=%r course_name=%r lesson_number=%r - this is a "
                    "retrieval outage, not a legitimately empty corpus",
                    query,
                    course_name,
                    lesson_number,
                )
                return (
                    "The search service is temporarily unavailable. "
                    "Please try again shortly."
                )
            filter_info = ""
            if course_name:
                filter_info += f" in course '{course_name}'"
            if lesson_number:
                filter_info += f" in lesson {lesson_number}"
            return f"No relevant content found{filter_info}."

        return self._format_results(results)

    def _format_results(self, results: List[Tuple[str, Dict, float]]) -> str:
        formatted = []
        sources = []
        chunks = []
        for doc, meta, ce_score in results:
            course_title = meta.get("course_title", "unknown")
            lesson_num = meta.get("lesson_number")
            header = f"[{course_title}"
            if lesson_num is not None:
                header += f" - Lesson {lesson_num}"
            header += "]"
            source = course_title
            if lesson_num is not None:
                source += f" - Lesson {lesson_num}"
            sources.append(source)
            formatted.append(f"{header}\n{doc}")
            # sigmoid normalizes cross-encoder logit → [0, 1] for display
            display_score = round(1.0 / (1.0 + math.exp(-ce_score)), 3)
            chunks.append(
                {
                    "text": doc,
                    "course": course_title,
                    "lesson": lesson_num,
                    "score": display_score,
                }
            )
        self.last_sources = sources
        self.last_chunks = chunks
        return "\n\n".join(formatted)


class ToolManager:
    """Manages available tools for the AI"""

    def __init__(self):
        self.tools = {}

    def register_tool(self, tool: Tool):
        """Register any tool that implements the Tool interface"""
        tool_def = tool.get_tool_definition()
        tool_name = tool_def.get("name")
        if not tool_name:
            raise ValueError("Tool must have a 'name' in its definition")
        self.tools[tool_name] = tool

    def get_tool_definitions(self) -> list:
        """Get all tool definitions for Anthropic tool calling"""
        return [tool.get_tool_definition() for tool in self.tools.values()]

    def execute_tool(self, tool_name: str, **kwargs) -> str:
        """Execute a tool by name with given parameters"""
        if tool_name not in self.tools:
            return f"Tool '{tool_name}' not found"

        return self.tools[tool_name].execute(**kwargs)

    def get_last_sources(self) -> list:
        """Get sources from the last search operation"""
        # Check all tools for last_sources attribute
        for tool in self.tools.values():
            if hasattr(tool, "last_sources") and tool.last_sources:
                return tool.last_sources
        return []

    def reset_sources(self):
        """Reset sources from all tools that track sources"""
        for tool in self.tools.values():
            if hasattr(tool, "last_sources"):
                tool.last_sources = []
