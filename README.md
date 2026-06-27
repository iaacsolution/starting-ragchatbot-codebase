---
title: Course RAG Chatbot
emoji: 🎓
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# Course RAG Chatbot

> Assistant conversationnel sur des cours IA DeepLearning.ai — réponses sourcées, évaluation continue, stack d'observabilité complète.

![Python](https://img.shields.io/badge/Python-3.13+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.116-green) ![Claude](https://img.shields.io/badge/Anthropic-Claude%20Haiku-orange) ![RAGAS](https://img.shields.io/badge/RAGAS-faithfulness%2093%25-brightgreen) ![Docker](https://img.shields.io/badge/Docker-Compose-blue) ![HF Spaces](https://img.shields.io/badge/HuggingFace-Spaces-yellow)

---

## Ce que ça fait

Tu poses une question en langage naturel sur des cours IA (Anthropic Claude, MCP, RAG, Agent Skills, Claude Code...). Le système retrouve les passages pertinents dans les transcriptions via recherche vectorielle multilingue, génère une réponse sourcée en streaming, et évalue la fidélité en temps réel.

```
"Comment fonctionne le tool use dans Claude ?"
→ recherche vectorielle multilingue (paraphrase-multilingual-MiniLM-L12-v2)
→ Claude Haiku synthétise avec les sources (tool use, max 2 rounds)
→ RAGAS faithfulness : 0.93 ✅  →  auto-tune MAX_RESULTS
```

---

## Fonctionnalités

### RAG Pipeline — améliorations progressives

| Niveau | Feature | Impact |
|--------|---------|--------|
| 1 | **Chunking sémantique** — split sur headers markdown (`###`) avant normalisation, chaque section devient son propre vecteur | recall exact sur termes techniques |
| 2 | **Auto-tune MAX_RESULTS** — ajuste automatiquement le nombre de chunks selon la moyenne glissante RAGAS (10 dernières requêtes) | fidélité stable |
| 3 | **Multi-round tool calling** — jusqu'à 2 recherches séquentielles par requête pour les comparaisons cross-cours | questions complexes résolues |

### Observabilité complète

- **RAGAS faithfulness** calculé en arrière-plan sur chaque requête, badge coloré inline dans le chat (vert ≥80%, orange ≥60%, rouge <60%)
- **Prometheus** scrape `/metrics` toutes les 15s — distributions de scores, latences
- **Grafana** dashboards préconfigurés (port 3001)
- **Phoenix OTEL** traces de chaque appel LLM Anthropic (port 6006)

### Guardrails qualité

- **INDEX_VERSION** — version de schéma persistée dans ChromaDB ; bump automatique du ré-index si la version change (chunking ou docs mis à jour)
- **Scope restriction** — le system prompt refuse les questions hors cours et les tentatives de prompt injection
- **Pre-indexing build-time** — ChromaDB baked dans l'image Docker, démarrage instantané (0 indexation à chaud)

### UX

- Streaming SSE — les tokens arrivent au fur et à mesure
- **Bouton Copier** sur chaque réponse (clipboard → checkmark)
- Thumbs up/down sur chaque réponse → feedback persisté en JSON + `/api/feedback/summary`
- Toggle dark/light mode
- Historique de session

---

## Cours indexés (10 cours DeepLearning.ai / Anthropic)

- Building Towards Computer Use with Anthropic
- MCP: Build Rich-Context AI Apps with Anthropic
- Prompt Engineering with Anthropic Claude
- Tool Use with Claude
- Agent Skills with Anthropic
- Claude Code: A Highly Agentic Coding Assistant
- Agent Skills Guide
- RAG en Production
- Bases de Récupération d'Informations et de Recherche (TF-IDF, BM25, RRF, embeddings)
- Cours sur le RAG — DeepLearning.ai (HNSW, Weaviate, chunking, re-ranking, ColBERT)

---

## Stack

```
Frontend    Vanilla JS + SSE streaming
Backend     FastAPI · uvicorn · Python 3.13
LLM         Anthropic Claude Haiku (tool use, max 2 rounds)
Fallback    Ollama llama3.2:1b (inférence locale)
Vector DB   ChromaDB (pré-indexé au build, persisté sur volume Docker)
Embeddings  paraphrase-multilingual-MiniLM-L12-v2 (FR + EN)
Evals       RAGAS faithfulness (LangchainLLMWrapper + ChatAnthropic)
Observ.     Prometheus · Grafana · Arize Phoenix (OTEL)
Deploy      HF Spaces (Docker) · Docker Compose local (6 services)
```

---

## Architecture

```
Utilisateur
    │
    ▼
FastAPI /api/query/stream
    │
    ├─ RAGSystem.query()
    │       ├─ AIGenerator  (tool use, max 2 rounds)
    │       │       └─ CourseSearchTool → ChromaDB
    │       └─ SessionManager (historique)
    │
    ├─ ragas_evaluator      ← async, timeout 60s, auto-tune MAX_RESULTS
    │       └─ Prometheus metrics
    │
    └─ Phoenix OTEL traces
```

---

## Déploiement

### HF Spaces (production)

Le Space est déployé sur [HuggingFace Spaces](https://huggingface.co/spaces/Krebs/claude-courses-assistant) — ChromaDB pré-indexé dans l'image, démarrage en ~30s.

```bash
git push origin main && git push hf main
```

### Docker local (dev complet avec observabilité)

```bash
cp .env.example .env
# Ajouter ANTHROPIC_API_KEY dans .env

docker compose up --build   # premier lancement (~2 min, pull Ollama)
docker compose up           # lancements suivants
```

| Service | URL |
|---------|-----|
| Chatbot | http://localhost:8000 |
| Grafana | http://localhost:3001 · admin/admin |
| Phoenix | http://localhost:6006 |
| Prometheus | http://localhost:9091 |

### Local sans Docker (dev rapide)

```bash
uv sync
ollama serve                          # terminal séparé
cd backend && uv run uvicorn app:app --reload --port 8000
```

---

## Ajouter un cours

Déposer un `.txt` dans `docs/` au format suivant, bumper `INDEX_VERSION` dans `config.py`, et redémarrer — indexation automatique et idempotente :

```
Course Title: <titre>
Course Instructor: <nom>

### Lesson 1: <titre>
<contenu>...

### Lesson 2: <titre>
<contenu>...
```

---

## Tests

```bash
cd backend && uv run pytest tests/ -v
# Tests comportementaux sur AIGenerator (multi-round tool calling)
```

---

## Variables d'environnement

| Variable | Défaut | Description |
|----------|--------|-------------|
| `ANTHROPIC_API_KEY` | — | **Requis** |
| `ANTHROPIC_MODEL` | `claude-haiku-4-5-20251001` | Modèle principal |
| `OLLAMA_MODEL` | `llama3.2:1b` | Fallback local |
| `PHOENIX_ENDPOINT` | `http://localhost:6006/v1/traces` | Traces OTEL |

---

## Patterns d'architecture

| Pattern | Où | Pourquoi |
|---|---|---|
| Facade | `RAGSystem` | Interface unique `query()` sur VectorStore + AIGenerator |
| Strategy | `AIGenerator` / `OllamaGenerator` | Swap LLM provider sans changer le code métier |
| Observer | `ragas_evaluator` + Prometheus | Métriques découplées des requêtes |
| Template Method | `RAGSystem.query()` | Séquence fixe : retrieve → generate → eval |
| Singleton | `config` | Un seul objet Config partagé par tous les composants |
