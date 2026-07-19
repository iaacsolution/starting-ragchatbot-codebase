"""
Batch RAGAS evaluation script.

Usage (from backend/):
    uv run python run_eval.py

Runs 20 representative questions through the RAG pipeline (15 original +
5 added 2026-07-19: 3 cross-lingual, 2 compound cross-course), evaluates
Faithfulness and AnswerRelevancy with RAGAS, and writes a JSON report
to ../eval_results.json plus a console summary table.
"""

import json
import os
import sys
import time
import types

# ── VertexAI stub (same trick as ragas_evaluator.py) ──────────────────────────
if "langchain_community.chat_models.vertexai" not in sys.modules:
    _stub = types.ModuleType("langchain_community.chat_models.vertexai")
    _stub.ChatVertexAI = type("ChatVertexAI", (), {})
    sys.modules["langchain_community.chat_models.vertexai"] = _stub

from config import config
from rag_system import RAGSystem

# ── Test dataset ───────────────────────────────────────────────────────────────
TEST_QUESTIONS = [
    # RAG & Retrieval
    "What is RAG and what problem does it solve compared to a plain LLM?",
    "How does HNSW work and why is it faster than exhaustive kNN for vector search?",
    "What are the main chunking strategies to improve retrieval quality in RAG?",
    "What is the difference between a bi-encoder and a cross-encoder?",
    "How does hybrid search combine BM25 and vector search, and what is RRF?",
    "What is query expansion and how does it improve retrieval recall?",
    "How does re-ranking improve the quality of retrieved documents in a RAG pipeline?",
    "What metrics are used to evaluate a RAG system (faithfulness, relevancy, precision)?",
    # Prompt Engineering
    "What is prompt compression and when should you use it?",
    "How does chain-of-thought prompting improve LLM reasoning?",
    # Anthropic / Claude
    "What are the main capabilities of Claude Code as a coding assistant?",
    "What is MCP and what problem does it solve for AI applications?",
    "How does computer use work with Claude and what are its main components?",
    "What are agent skills in the Anthropic framework?",
    # Production RAG
    "What are the main challenges of deploying a RAG system in production?",
    # --- Cross-lingual (FR question / EN-only corpus) ---
    "Dans les transcriptions de cours indexées, quel est le texte EXACT de l'avis "
    "client utilisé comme exemple pour l'analyse de sentiment avec le téléphone "
    "Acme ? Cite-le mot pour mot.",
    "Selon la démo SQLite présentée dans le cours sur MCP, combien de produits, "
    "d'utilisateurs et de commandes contenait la base de données ?",
    "Dans le cours sur la recherche avancée avec Chroma, combien de chunks "
    "obtient-on en découpant le rapport annuel Microsoft d'abord par "
    "caractères, puis par tokens ?",
    # --- Compound cross-course (not true sequential multi-hop, see caveat) ---
    "According to the MCP course, how many products and users appear in the "
    "SQLite demo database? And according to the Agent Skills course, what are "
    "the three components the Claude Agent SDK provides for working with skills?",
    "What is the exact customer review text used as the sentiment analysis "
    "example with the Acme phone (Computer Use course), and how many Airbnb "
    "listings are in the dataset used in the Prompt Compression course?",
]


def _distinct_courses(sources: list[str]) -> int:
    """Count distinct course titles in a list of 'Course Title - Lesson N' source strings."""
    return len({s.split(" - Lesson ")[0] for s in sources})


def run_pipeline(rag: RAGSystem) -> list[dict]:
    """Run every question through the RAG pipeline and collect (q, answer, contexts)."""
    rows = []
    for i, question in enumerate(TEST_QUESTIONS, 1):
        print(
            f"  [{i:02d}/{len(TEST_QUESTIONS)}] {question[:70]}…", end=" ", flush=True
        )
        t0 = time.perf_counter()
        answer, sources = rag.query(question)
        elapsed = time.perf_counter() - t0
        contexts = rag.last_contexts[:]
        print(f"({elapsed:.1f}s, {len(contexts)} ctx)")
        rows.append(
            {
                "question": question,
                "answer": answer,
                "contexts": contexts,
                "sources": sources,
                "latency_s": round(elapsed, 2),
                "n_chunks": len(sources),
                "answer_preview": answer[:300],
                "n_distinct_courses": _distinct_courses(sources),
            }
        )
    return rows


def ragas_evaluate(rows: list[dict]) -> list[dict]:
    """Run RAGAS Faithfulness on all rows. Returns rows enriched with scores."""
    from ragas import evaluate, EvaluationDataset, SingleTurnSample
    from ragas.metrics import Faithfulness
    from ragas.llms import LangchainLLMWrapper
    from langchain_anthropic import ChatAnthropic

    llm = LangchainLLMWrapper(
        ChatAnthropic(model=config.ANTHROPIC_MODEL, api_key=config.ANTHROPIC_API_KEY)
    )
    metric = Faithfulness(llm=llm)

    samples = [
        SingleTurnSample(
            user_input=r["question"],
            response=r["answer"],
            retrieved_contexts=r["contexts"],
        )
        for r in rows
    ]
    dataset = EvaluationDataset(samples=samples)

    print("\nRunning RAGAS Faithfulness on all samples…")
    result = evaluate(dataset=dataset, metrics=[metric])
    df = result.to_pandas()

    for i, row in enumerate(rows):
        row["faithfulness"] = round(float(df["faithfulness"].iloc[i]), 3)

    return rows


def print_report(rows: list[dict]) -> None:
    scores = [r["faithfulness"] for r in rows]
    avg = sum(scores) / len(scores)

    sep = "=" * 72
    print(f"\n{sep}")
    print(f"{'RAGAS EVALUATION REPORT':^72}")
    print(sep)
    print(f"  Questions tested : {len(rows)}")
    print(f"  Avg faithfulness : {avg:.3f}  ({avg*100:.0f}%)")
    failing = [r for r in rows if r["faithfulness"] < 0.6]
    print(f"  Failing (<0.6)   : {len(failing)}")
    print("-" * 72)

    flag = lambda s: "OK" if s >= 0.8 else ("~~ " if s >= 0.6 else "!!")
    for i, r in enumerate(rows, 1):
        s = r["faithfulness"]
        q = r["question"][:58].ljust(58)
        print(f"  [{flag(s)}] [{i:02d}] {q}  {s:.3f}")

    if failing:
        print("\n  FAILING questions (faithfulness < 0.6):")
        for r in failing:
            print(f"    - {r['question']}")

    print(sep)


def save_report(rows: list[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "model": config.ANTHROPIC_MODEL,
                "n_questions": len(rows),
                "avg_faithfulness": round(
                    sum(r["faithfulness"] for r in rows) / len(rows), 3
                ),
                "results": rows,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"\n  Report saved -> {path}")


def main():
    print("Initializing RAG system…")
    rag = RAGSystem(config)

    docs_path = "../docs"
    if os.path.exists(docs_path):
        courses, chunks = rag.add_course_folder(docs_path)
        print(f"  Loaded {courses} new courses ({chunks} chunks)\n")

    print(f"Running {len(TEST_QUESTIONS)} test questions…")
    rows = run_pipeline(rag)

    rows = ragas_evaluate(rows)
    print_report(rows)
    save_report(rows, "../eval_results.json")


if __name__ == "__main__":
    main()
