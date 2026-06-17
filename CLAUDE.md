# CLAUDE.md — Course Materials RAG System

## Contexte Métier

Ce système est un **assistant conversationnel sur des cours d'ingénierie IA** (DeepLearning.ai). Il permet à un apprenant de poser des questions en langage naturel et d'obtenir des réponses précises et sourcées depuis les transcriptions de cours.

**Domaine couvert par les cours :**
- APIs Anthropic Claude (tool use, computer use, MCP)
- Architecture RAG et ChromaDB (vector search, embeddings, retrieval avancé)
- Prompt engineering (compression, chain-of-thought, n-shot, optimisation de requêtes)

**Utilisateur cible :** Développeur ou étudiant ayant suivi des cours IA et souhaitant interroger leur contenu rapidement.

**Décisions métier à respecter :**
- Réponses courtes, sourcées, pédagogiques — pas de verbosité
- Pas de réponse inventée : si le contenu n'est pas dans la base, le dire clairement
- Le système est mono-domaine (les cours chargés) — ne pas dériver vers des réponses génériques hors cours

## Commandes de développement

```bash
# Développement local (Ollama doit tourner dans un autre terminal)
uv sync
ollama serve
cd backend && uv run uvicorn app:app --reload --port 8000

# Production Docker
docker compose up --build   # premier lancement (télécharge le modèle Ollama)
docker compose up           # lancements suivants
```

## Architecture

```
Utilisateur → FastAPI (backend/app.py)
                → RAGSystem.query()
                     → OllamaGenerator  ← SYSTEM_PROMPT + détection JSON tool call
                          → CourseSearchTool → VectorStore (ChromaDB)
                     ← réponse + sources
```

Fichiers clés :
- `backend/rag_system.py` — orchestrateur principal
- `backend/ollama_generator.py` — intégration Ollama, SYSTEM_PROMPT, parsing des tool calls
- `backend/vector_store.py` — opérations ChromaDB (add / search)
- `backend/config.py` — tous les paramètres réglables (CHUNK_SIZE, MAX_RESULTS…)
- `docs/` — fichiers .txt des cours (chargés automatiquement au démarrage)

## Production

Docker Compose (`docker compose up --build`) :
- Service `app` : FastAPI + uvicorn (port 8000)
- Service `ollama` : inférence LLM locale (port 11434)
- Volume `chroma_data` : persiste ChromaDB entre les redémarrages
- Volume `ollama_data` : met en cache les poids du modèle
- `entrypoint.sh` : attend Ollama, pull le modèle si absent, démarre uvicorn

## Contraintes non-évidentes

- **Le backend tourne depuis `backend/`** — imports relatifs, chemins `../docs` et `../frontend` supposent ce répertoire de travail.
- **Une seule recherche par query** — le system prompt limite le LLM à un appel d'outil par tour, intentionnel pour éviter les boucles.
- **ChromaDB est mono-processus** — `--workers 1` en prod ; ne pas scaler horizontalement.
- **Idempotence des documents** — `add_course_folder()` ignore les cours déjà indexés ; sûr de redémarrer sans dupliquer.

## Ajouter du contenu métier

Déposer un fichier `.txt` dans `docs/` au format suivant, puis redémarrer le serveur :

```
Course Title: <titre>
Course Instructor: <nom>

Lesson 1: <titre>
<contenu>...

Lesson 2: <titre>
<contenu>...
```

Aucun changement de code requis.
