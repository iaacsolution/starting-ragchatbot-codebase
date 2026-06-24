import anthropic

_SYSTEM = """Tu es un optimiseur de requêtes pour un système RAG de cours IA (DeepLearning.ai / Anthropic).

Ton rôle : réécrire la question utilisateur pour maximiser la similarité sémantique avec les chunks de cours indexés dans ChromaDB.

Règles :
- Développe les abréviations (skills → Agent Skills, SDK → Claude Agent SDK)
- Ajoute les termes techniques du domaine si pertinents
- Conserve la langue originale de la question
- Retourne UNIQUEMENT la question réécrite, sans explication ni ponctuation superflue"""


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
                    "content": f"Cours disponibles :\n{titles_str}\n\nQuestion : {query}",
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
