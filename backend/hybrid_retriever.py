from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer


def _reciprocal_rank_fusion(
    *ranked_lists: List[Tuple[int, float]], k: int = 60
) -> List[Tuple[int, float]]:
    scores: Dict[int, float] = {}
    for ranked in ranked_lists:
        for rank, (idx, _) in enumerate(ranked):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


class HybridRetriever:
    """
    Three-stage retriever:
      1. BM25 (keyword) + Euclidean similarity (dense) in parallel
      2. RRF fusion to merge both ranked lists
      3. Cross-encoder reranking on the fused candidates
    """

    def __init__(
        self,
        vector_store,
        cross_encoder_model: str,
        embedding_model: str,
        candidates: int = 20,
    ) -> None:
        self.store = vector_store
        self.candidates = candidates
        self.encoder = SentenceTransformer(embedding_model)
        self.cross_encoder = CrossEncoder(cross_encoder_model)
        self._corpus: List[str] = []
        self._meta: List[Dict] = []
        self._embeddings: Optional[np.ndarray] = None
        self._bm25: Optional[BM25Okapi] = None

    def reset_cache(self) -> None:
        """Invalidate the in-memory corpus cache after new documents are indexed."""
        self._corpus = []
        self._meta = []
        self._embeddings = None
        self._bm25 = None

    def _load_corpus(self) -> None:
        if self._bm25 is not None:
            return

        raw = self.store.get_all_content()
        self._corpus = raw.get("documents") or []
        self._meta = raw.get("metadatas") or []

        if not self._corpus:
            self._bm25 = BM25Okapi([[""]])
            self._embeddings = np.empty((0, 384))
            return

        self._embeddings = self.encoder.encode(
            self._corpus,
            batch_size=64,
            show_progress_bar=False,
            normalize_embeddings=False,
        )
        tokenized = [doc.lower().split() for doc in self._corpus]
        self._bm25 = BM25Okapi(tokenized)

    # ------------------------------------------------------------------
    # Individual retrievers
    # ------------------------------------------------------------------

    def _bm25_rank(self, query: str) -> List[Tuple[int, float]]:
        tokens = query.lower().split()
        scores = self._bm25.get_scores(tokens)
        order = np.argsort(scores)[::-1]
        return [(int(i), float(scores[i])) for i in order[: self.candidates]]

    def _euclidean_rank(self, query: str) -> List[Tuple[int, float]]:
        q_emb = self.encoder.encode([query], normalize_embeddings=False)[0]
        dists = np.linalg.norm(self._embeddings - q_emb, axis=1)
        order = np.argsort(dists)
        return [(int(i), float(dists[i])) for i in order[: self.candidates]]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        k: int = 5,
        course_title: Optional[str] = None,
        lesson_number: Optional[int] = None,
    ) -> List[Tuple[str, Dict]]:
        """
        Return top-k (document, metadata) pairs after hybrid retrieval
        and cross-encoder reranking.
        """
        self._load_corpus()
        if not self._corpus:
            return []

        bm25_ranked = self._bm25_rank(query)
        eucl_ranked = self._euclidean_rank(query)
        fused = _reciprocal_rank_fusion(bm25_ranked, eucl_ranked)

        if course_title or lesson_number is not None:
            fused = [
                (idx, s)
                for idx, s in fused
                if self._matches_filter(idx, course_title, lesson_number)
            ]

        candidates = fused[: self.candidates]
        if not candidates:
            return []

        pairs = [(query, self._corpus[idx]) for idx, _ in candidates]
        ce_scores = self.cross_encoder.predict(pairs)

        reranked = sorted(zip(candidates, ce_scores), key=lambda x: x[1], reverse=True)
        return [(self._corpus[idx], self._meta[idx]) for (idx, _), _ in reranked[:k]]

    def _matches_filter(
        self, idx: int, course_title: Optional[str], lesson_number: Optional[int]
    ) -> bool:
        meta = self._meta[idx]
        if course_title and meta.get("course_title") != course_title:
            return False
        if lesson_number is not None and meta.get("lesson_number") != lesson_number:
            return False
        return True
