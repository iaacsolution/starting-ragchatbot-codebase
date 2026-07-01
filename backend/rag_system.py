from typing import List, Tuple, Optional, Dict
import os
from document_processor import DocumentProcessor
from vector_store import VectorStore
from ai_generator import AIGenerator
from session_manager import SessionManager
from hybrid_retriever import HybridRetriever
from search_tools import ToolManager, HybridSearchTool
from models import Course, Lesson, CourseChunk


class RAGSystem:
    """Main orchestrator for the Retrieval-Augmented Generation system"""

    def __init__(self, config):
        self.config = config

        # Initialize core components
        self.document_processor = DocumentProcessor(
            config.CHUNK_SIZE, config.CHUNK_OVERLAP
        )
        self.vector_store = VectorStore(
            config.CHROMA_PATH, config.EMBEDDING_MODEL, config.MAX_RESULTS
        )
        self.ai_generator = AIGenerator(
            config.ANTHROPIC_API_KEY, config.ANTHROPIC_MODEL
        )
        self.session_manager = SessionManager(config.MAX_HISTORY)

        # Initialize hybrid retriever and search tool
        self.hybrid_retriever = HybridRetriever(
            vector_store=self.vector_store,
            cross_encoder_model=config.CROSS_ENCODER_MODEL,
            embedding_model=config.EMBEDDING_MODEL,
            candidates=config.HYBRID_CANDIDATES,
        )
        self.tool_manager = ToolManager()
        self.search_tool = HybridSearchTool(self.vector_store, self.hybrid_retriever)
        self.tool_manager.register_tool(self.search_tool)

    def add_course_document(self, file_path: str) -> Tuple[Course, int]:
        """
        Add a single course document to the knowledge base.

        Args:
            file_path: Path to the course document

        Returns:
            Tuple of (Course object, number of chunks created)
        """
        try:
            # Process the document
            course, course_chunks = self.document_processor.process_course_document(
                file_path
            )

            # Add course metadata to vector store for semantic search
            self.vector_store.add_course_metadata(course)

            # Add course content chunks to vector store
            self.vector_store.add_course_content(course_chunks)

            return course, len(course_chunks)
        except Exception as e:
            print(f"Error processing course document {file_path}: {e}")
            return None, 0

    def add_course_folder(
        self, folder_path: str, clear_existing: bool = False
    ) -> Tuple[int, int]:
        """
        Add all course documents from a folder.

        Args:
            folder_path: Path to folder containing course documents
            clear_existing: Whether to clear existing data first

        Returns:
            Tuple of (total courses added, total chunks created)
        """
        total_courses = 0
        total_chunks = 0

        # Auto-detect schema version mismatch → force re-index to avoid stale embeddings
        version_file = os.path.join(self.config.CHROMA_PATH, ".index_version")
        current_version = getattr(self.config, "INDEX_VERSION", "v1")
        if not clear_existing:
            if os.path.exists(version_file):
                stored = open(version_file).read().strip()
                if stored != current_version:
                    print(
                        f"[INDEX] Schema version mismatch ({stored} → {current_version}), re-indexing..."
                    )
                    clear_existing = True
            else:
                print(
                    f"[INDEX] No version file found, re-indexing with version {current_version}..."
                )
                clear_existing = True

        # Clear existing data if requested or version mismatch detected
        if clear_existing:
            print("Clearing existing data for fresh rebuild...")
            self.vector_store.clear_all_data()

        if not os.path.exists(folder_path):
            print(f"Folder {folder_path} does not exist")
            return 0, 0

        # Get existing course titles to avoid re-processing
        existing_course_titles = set(self.vector_store.get_existing_course_titles())

        # Process each file in the folder
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            if os.path.isfile(file_path) and file_name.lower().endswith(
                (".pdf", ".docx", ".txt")
            ):
                try:
                    # Check if this course might already exist
                    # We'll process the document to get the course ID, but only add if new
                    course, course_chunks = (
                        self.document_processor.process_course_document(file_path)
                    )

                    if course and course.title not in existing_course_titles:
                        # This is a new course - add it to the vector store
                        self.vector_store.add_course_metadata(course)
                        self.vector_store.add_course_content(course_chunks)
                        total_courses += 1
                        total_chunks += len(course_chunks)
                        print(
                            f"Added new course: {course.title} ({len(course_chunks)} chunks)"
                        )
                        existing_course_titles.add(course.title)
                    elif course:
                        print(f"Course already exists: {course.title} - skipping")
                except Exception as e:
                    print(f"Error processing {file_name}: {e}")

        # Persist version so next startup skips re-index unless version changes
        os.makedirs(self.config.CHROMA_PATH, exist_ok=True)
        with open(version_file, "w") as f:
            f.write(current_version)

        # Invalidate hybrid retriever corpus cache after indexing
        self.hybrid_retriever.reset_cache()

        return total_courses, total_chunks

    def query(
        self, query: str, session_id: Optional[str] = None
    ) -> Tuple[str, List[str]]:
        """
        Process a user query using the RAG system.
        Always retrieves from vector store first, then synthesizes with the LLM.
        """

        # Get conversation history if session exists
        history = None
        if session_id:
            history = self.session_manager.get_conversation_history(session_id)

        # Always search the vector store
        search_results = self.search_tool.execute(query=query)
        sources = self.search_tool.last_sources[:]
        self.search_tool.last_sources = []
        self.last_contexts = [search_results] if search_results else []

        # Build prompt with or without retrieved context
        if search_results and "No results found" not in search_results:
            prompt = (
                f"Use the following course content to answer the question.\n\n"
                f"Course content:\n{search_results}\n\n"
                f"Question: {query}\n\n"
                f"Answer based only on the course content above. "
                f"If the content does not answer the question, say so."
            )
        else:
            prompt = (
                f"Answer this question about AI/ML courses: {query}\n\n"
                f"No specific course content was found. Give a brief general answer "
                f"and suggest the user try a more specific question."
            )

        # Generate response
        response = self.ai_generator.generate_response(
            query=prompt,
            conversation_history=history,
        )

        # Update conversation history
        if session_id:
            self.session_manager.add_exchange(session_id, query, response)

        return response, sources

    def get_course_analytics(self) -> Dict:
        """Get analytics about the course catalog"""
        return {
            "total_courses": self.vector_store.get_course_count(),
            "course_titles": self.vector_store.get_existing_course_titles(),
        }
