---
name: Course RAG System
description: AI Agent Skills and Instructions for the Course Materials RAG System
type: agent
---

# Course Materials RAG System — Agent Guide

## Contexte Métier (lire en premier)

Ce système est un **assistant pédagogique RAG** pour 4 cours d'ingénierie IA (DeepLearning.ai) :

| Fichier | Cours |
|---------|-------|
| course1_script.txt | Building Towards Computer Use with Anthropic |
| course2_script.txt | MCP: Build Rich-Context AI Apps with Anthropic |
| course3_script.txt | Advanced Retrieval for AI with Chroma |
| course4_script.txt | Prompt Compression and Query Optimization |

**Contraintes métier à respecter dans toute modification :**
- Les réponses doivent rester courtes, sourcées, factuelles
- Le système est mono-domaine — ne pas étendre vers un chatbot généraliste sans accord explicite
- La qualité de retrieval (CHUNK_SIZE, MAX_RESULTS, embeddings) impacte directement la pertinence des réponses

## Documentation principale

Lire **[AGENTS.md](../AGENTS.md)** pour l'architecture complète, les endpoints API et les conventions de code.

## Modes de déploiement

| Mode | Commande | Usage |
|------|----------|-------|
| Dev local | `cd backend && uv run uvicorn app:app --reload --port 8000` | Développement avec Ollama local |
| Production | `docker compose up --build` | Déploiement on-premise complet |

En production Docker :
- `app` (FastAPI, port 8000) + `ollama` (LLM local, port 11434)
- Volumes persistants : `chroma_data` (ChromaDB), `ollama_data` (poids modèle)
- `entrypoint.sh` orchestre le démarrage : attend Ollama → pull modèle → démarre uvicorn

## Skills disponibles

| Skill | Quand l'utiliser |
|-------|-----------------|
| [setup-ollama.md](skills/setup-ollama.md) | Installer Ollama et télécharger le modèle |
| [run-dev-server.md](skills/run-dev-server.md) | Démarrer le serveur de développement |
| [load-course-documents.md](skills/load-course-documents.md) | Ajouter de nouveaux cours au corpus |
| [frontend-modifications.md](skills/frontend-modifications.md) | Modifier l'interface web |

## Règles de développement

**A faire :**
- Démarrer Ollama avant le serveur RAG (`ollama serve`)
- Utiliser des imports relatifs dans le backend
- Exécuter les commandes backend depuis le dossier `backend/`
- Utiliser les type hints Pydantic sur tous les modèles API
- Tester les changements d'API via `/docs`

**A ne pas faire :**
- Scaler le serveur horizontalement (ChromaDB est mono-processus)
- Supprimer `chroma_db/` sans backup
- Hardcoder des valeurs de configuration (utiliser `config.py`)
- Modifier le SYSTEM_PROMPT sans tester l'impact sur la qualité des réponses métier
- Ajouter des fonctionnalités génériques non liées aux cours (hors du domaine métier)

## Ajouter du contenu métier

Déposer un `.txt` dans `docs/` au format :
```
Course Title: <titre>
Course Instructor: <nom>

Lesson 1: <titre>
<contenu>

Lesson 2: <titre>
<contenu>
```
Redémarrer le serveur — le cours est indexé automatiquement. Aucun code à modifier.
