"""Run at Docker build time to bake the ChromaDB index into the image."""

import sys
import os

sys.path.insert(0, "/app/backend")
os.chdir("/app/backend")

from config import Config
from rag_system import RAGSystem

cfg = Config()
rag = RAGSystem(cfg)
courses, chunks = rag.add_course_folder("/app/docs", clear_existing=True)
print(f"[PREINDEX] Indexed {courses} courses, {chunks} chunks into {cfg.CHROMA_PATH}")
print(f"[PREINDEX] INDEX_VERSION={cfg.INDEX_VERSION} written to .index_version")
