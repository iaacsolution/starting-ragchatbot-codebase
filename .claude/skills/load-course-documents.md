---
name: Load Course Documents
description: Add course documents to the vector database
type: skill
---

# Load Course Documents Skill

Helps add new course materials to the RAG system's knowledge base.

## Prerequisites
- Server must be running (via `run-dev-server` skill)
- New course file in plain text format (.txt)
- File should be in `docs/` folder

## File Format Requirements

Course document should contain:
- Course title on first line (or identifiable metadata)
- Content organized by lessons with markers like `[Lesson N]`
- Plain text format (UTF-8 encoding)
- Typical size: 50KB-150KB per course

### Example Structure
```
Advanced Python Programming

[Lesson 1: Introduction]
In this lesson, we'll cover the basics...

[Lesson 2: Data Structures]
Lists, tuples, and dictionaries are core...
```

## Loading Process

### Automatic (on Server Startup)
1. Place .txt files in `docs/` folder
2. Restart server - documents auto-load on startup
3. Check logs for: `Loaded X courses with Y chunks`

### Manual (Python Script)
```python
from backend.rag_system import RAGSystem
from backend.config import config

rag = RAGSystem(config)
course, chunks = rag.add_course_document("docs/new_course.txt")
print(f"Added {len(chunks)} chunks from '{course.title}'")
```

## Verification
After loading, verify via:
- Check `/api/courses` endpoint returns updated list
- Frontend sidebar shows new course in "Courses" section
- Query the new material: "What is covered in [course name]?"

## Rebuild Vector Store
To clear and reload all documents:
```bash
rm -rf chroma_db/        # Remove existing database
# Restart server
```

## Supported Document Formats
- **.txt**: Plain text (primary format)
- **Encoding**: UTF-8 or UTF-8 with error handling
- **Size limit**: No hard limit, but very large files (>500KB) may be slow to process
