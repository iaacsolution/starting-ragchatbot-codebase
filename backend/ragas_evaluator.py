from concurrent.futures import ThreadPoolExecutor
from prometheus_client import Gauge, Histogram

faithfulness_gauge = Gauge(
    "ragas_faithfulness", "RAGAS faithfulness score (last query)"
)
relevancy_gauge = Gauge(
    "ragas_answer_relevancy", "RAGAS answer relevancy score (last query)"
)
faithfulness_hist = Histogram(
    "ragas_faithfulness_hist",
    "RAGAS faithfulness distribution",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)
relevancy_hist = Histogram(
    "ragas_answer_relevancy_hist",
    "RAGAS answer relevancy distribution",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

_executor = ThreadPoolExecutor(max_workers=1)

# Last computed scores — read by GET /api/metrics/ragas
last_scores: dict = {"faithfulness": None, "relevancy": None, "ready": False}

# Rolling history for auto-tuning (last 10 faithfulness scores)
_score_history: list[float] = []
_HISTORY_SIZE = 10
_MIN_RESULTS = 2
_MAX_RESULTS_CAP = 10


def _auto_tune(f: float) -> None:
    """Adjust MAX_RESULTS based on rolling faithfulness average."""
    global _score_history
    _score_history.append(f)
    if len(_score_history) > _HISTORY_SIZE:
        _score_history.pop(0)

    if len(_score_history) < _HISTORY_SIZE:
        return

    from config import config

    avg = sum(_score_history) / _HISTORY_SIZE
    if avg < 0.6 and config.MAX_RESULTS < _MAX_RESULTS_CAP:
        config.MAX_RESULTS += 1
        print(
            f"[AUTO-TUNE↑] avg_faithfulness={avg:.2f} → MAX_RESULTS={config.MAX_RESULTS}"
        )
    elif avg > 0.85 and config.MAX_RESULTS > _MIN_RESULTS:
        config.MAX_RESULTS -= 1
        print(
            f"[AUTO-TUNE↓] avg_faithfulness={avg:.2f} → MAX_RESULTS={config.MAX_RESULTS}"
        )


def _run_ragas(question: str, answer: str, contexts: list, api_key: str, model: str):
    global last_scores
    last_scores = {"faithfulness": None, "relevancy": None, "ready": False}
    try:
        # Stub missing Google Cloud optional dep before ragas imports it
        import sys
        import types

        if "langchain_community.chat_models.vertexai" not in sys.modules:
            _stub = types.ModuleType("langchain_community.chat_models.vertexai")
            _stub.ChatVertexAI = type("ChatVertexAI", (), {})
            sys.modules["langchain_community.chat_models.vertexai"] = _stub

        from ragas import evaluate, EvaluationDataset, SingleTurnSample
        from ragas.metrics import Faithfulness
        from ragas.llms import LangchainLLMWrapper
        from langchain_anthropic import ChatAnthropic

        llm = LangchainLLMWrapper(ChatAnthropic(model=model, api_key=api_key))
        sample = SingleTurnSample(
            user_input=question,
            response=answer,
            retrieved_contexts=contexts,
        )
        dataset = EvaluationDataset(samples=[sample])
        result = evaluate(
            dataset=dataset,
            metrics=[Faithfulness(llm=llm)],
        )
        scores = result.to_pandas()
        f = float(scores["faithfulness"].iloc[0])

        faithfulness_gauge.set(f)
        faithfulness_hist.observe(f)
        last_scores = {
            "faithfulness": round(f, 2),
            "relevancy": None,
            "ready": True,
        }
        _auto_tune(f)
    except Exception as e:
        print(f"RAGAS evaluation error: {e}")
        last_scores = {"faithfulness": None, "relevancy": None, "ready": True}


def evaluate_async(
    question: str, answer: str, contexts: list, api_key: str, model: str
):
    global last_scores
    last_scores = {"faithfulness": None, "relevancy": None, "ready": False}
    if contexts:
        _executor.submit(_run_ragas, question, answer, contexts, api_key, model)
    else:
        last_scores = {"faithfulness": None, "relevancy": None, "ready": True}
