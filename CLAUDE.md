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
                     → AIGenerator  ← SYSTEM_PROMPT + tool use Anthropic
                          → CourseSearchTool → VectorStore (ChromaDB)
                     ← réponse + sources
                → ragas_evaluator (background) → Prometheus metrics
                → Phoenix OTEL traces
```

Fichiers clés :
- `backend/rag_system.py` — orchestrateur principal (Facade)
- `backend/ai_generator.py` — intégration Anthropic Claude, SYSTEM_PROMPT, tool use
- `backend/ollama_generator.py` — fallback Ollama (Strategy alternative)
- `backend/vector_store.py` — opérations ChromaDB (add / search)
- `backend/config.py` — tous les paramètres réglables (CHUNK_SIZE, MAX_RESULTS…)
- `backend/ragas_evaluator.py` — évaluation RAGAS async + métriques Prometheus
- `docs/` — fichiers .txt des cours (chargés automatiquement au démarrage)

## Production

Docker Compose (`docker compose up --build`) :
- Service `app` : FastAPI + uvicorn (port 8000)
- Service `ollama` : inférence LLM locale de fallback (port 11434)
- Service `phoenix` : traces LLM Anthropic (port 6006)
- Service `prometheus` : scrape `/metrics` toutes les 15s (port 9091)
- Service `grafana` : dashboards (port 3001, admin/admin)
- Volume `chroma_data` : persiste ChromaDB entre les redémarrages
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

## Bonnes pratiques de développement 2026

### Principes généraux

- **Observability-first** — toute nouvelle feature expose des métriques Prometheus et des traces Phoenix dès le départ, pas en retard de phase.
- **Fail-fast explicite** — lever des exceptions métier claires plutôt que retourner `None` ou des chaînes vides silencieuses.
- **Typage strict** — annoter tous les paramètres et retours de fonctions publiques (`str`, `list[str]`, `tuple[str, list[str]]`). Pas de `Any` sauf à la frontière externe (JSON entrant).
- **Pas d'abstraction prématurée** — trois lignes similaires ne justifient pas une classe. Extraire quand le quatrième cas arrive.
- **Config centralisée** — tous les paramètres réglables passent par `config.py`. Aucune constante magique dans le code métier.
- **Tests sur le comportement, pas l'implémentation** — tester ce que la fonction retourne, pas comment elle le calcule. Mocker uniquement les I/O externes (API, DB).

### Patterns LLM / RAG (2026)

- **Context window budgeting** — calculer la taille du contexte avant l'appel LLM. Tronquer les chunks récupérés si nécessaire plutôt que dépasser la limite.
- **Tool use one-shot** — une seule invocation d'outil par tour (déjà appliqué). Les boucles multi-outils coûtent cher et dérivent.
- **Prompt versionné** — le `SYSTEM_PROMPT` est une constante de classe, pas une variable. Tout changement de prompt = nouveau commit.
- **Évaluation continue** — RAGAS tourne en arrière-plan sur chaque requête. Un score `faithfulness < 0.6` sur 10 requêtes consécutives = signal d'alerte à investiguer.
- **Séparation retrieval / generation** — ne jamais mélanger la logique de recherche vectorielle et la logique de génération dans la même fonction.

### Patterns Gang of Four appliqués à ce projet

| Pattern | Où | Pourquoi |
|---|---|---|
| **Facade** | `RAGSystem` | Cache la complexité de VectorStore + AIGenerator + SessionManager derrière une interface unique `query()` |
| **Strategy** | `AIGenerator` / `OllamaGenerator` | Interchangeable à la config — même interface, implémentation différente selon le provider LLM |
| **Template Method** | `RAGSystem.query()` | Séquence fixe : retrieve → prompt → generate → update history. Les étapes sont extensibles sans changer l'ordre |
| **Factory** | `ToolManager.register_tool()` | Enregistre et instancie les outils de recherche sans coupler le système au type concret |
| **Observer** | `ragas_evaluator` + Prometheus | Les métriques sont notifiées après chaque requête sans que `app.py` connaisse les détails d'évaluation |
| **Singleton** | `config` (instance globale) | Un seul objet Config chargé au démarrage, partagé par tous les composants |

### Anti-patterns à éviter

- **God object** — ne pas grossir `RAGSystem` avec de nouvelles responsabilités. Créer un nouveau composant si le périmètre change.
- **Prompt injection** — ne jamais concaténer directement du contenu utilisateur non nettoyé dans le system prompt.
- **Retry storms** — les appels LLM échoués ne doivent pas se retenter en boucle serrée. Exponentiel backoff ou fail immédiat.
- **Logging de données sensibles** — ne pas loguer les clés API, le contenu des conversations ou les chunks de cours en production.
