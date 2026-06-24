import anthropic

_SYSTEM = """You are a search query optimizer for an AI courses RAG system (DeepLearning.ai / Anthropic).

Your role: rewrite the user question to maximize semantic similarity with English course content chunks indexed in ChromaDB.

Rules:
- Always output the rewritten query in ENGLISH (course content is in English)
- Expand abbreviations (skills → Agent Skills, SDK → Claude Agent SDK, MCP → Model Context Protocol)
- Add relevant technical domain terms if helpful
- Return ONLY the rewritten query, no explanation"""


def rewrite(query: str, api_key: str, course_titles: list[str]) -> str:
    """Rewrite user query to improve semantic search recall. Returns original on failure."""
    try:
        titles_str = "\n".join(f"- {t}" for t in course_titles)
        client = anthropic.Anthropic(api_key=api_key or None)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=120,
            system=_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": f"Available courses:\n{titles_str}\n\nUser question: {query}",
                }
            ],
        )
        rewritten = response.content[0].text.strip()
        if rewritten and rewritten != query:
            print(f"[REWRITE] '{query}' → '{rewritten}'")
        return rewritten or query
    except Exception as e:
        print(f"[REWRITE] error: {e}")
        return query
