# app/memory/search.py
"""MemorySearchManager - Hybrid RAG: vector search (Ollama) + BM25 keyword search.

Reference: OpenClaw's memory-search plugin with hybrid retrieval:
- Vector search: semantic similarity via Ollama qwen3-embedding:0.6b
- BM25: keyword-based relevance scoring
- RRF fusion: Reciprocal Rank Fusion to combine rankings
- Temporal decay: newer documents get higher scores
"""
import aiohttp
import asyncio
import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import get_settings


@dataclass
class SearchResult:
    """A single search result."""
    chunk: str
    score: float
    doc_path: str
    date: Optional[datetime] = None


class MemorySearchManager:
    """Hybrid RAG: vector + BM25 with RRF fusion and temporal decay.

    Uses Ollama qwen3-embedding:0.6b for semantic embeddings.
    Falls back to BM25-only if Ollama is unavailable.
    """

    def __init__(
        self,
        memory_dir: Optional[str] = None,
        ollama_base_url: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ):
        settings = get_settings()
        if memory_dir is None:
            memory_dir = settings.memory_dir
        self.memory_dir = Path(memory_dir)
        self.ollama_base_url = ollama_base_url or settings.ollama_base_url
        self.embedding_model = embedding_model or settings.embedding_model
        self._embedding_cache: Dict[str, List[float]] = {}
        self._bm25_doc_freq: Dict[str, int] = {}
        self._bm25_avgdl: float = 0.0
        self._bm25_k1 = settings.rag_bm25_k1
        self._bm25_b = settings.rag_bm25_b
        self._rrf_k = settings.rag_rrf_k
        self._temporal_decay_days = settings.rag_temporal_decay_days
        self._total_docs = 0

    async def embed(self, text: str) -> Optional[List[float]]:
        """Get embedding via Ollama qwen3-embedding:0.6b.

        Returns None if Ollama is unavailable.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_base_url}/api/embeddings",
                    json={"model": self.embedding_model, "prompt": text},
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("embedding")
                    else:
                        return None
        except Exception:
            return None

    async def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """Hybrid search: BM25 + vector similarity with RRF fusion."""
        docs = self._load_all_docs()
        if not docs:
            return []

        if not self._bm25_doc_freq:
            self._build_bm25_index(docs)

        bm25_results = self._bm25_search(query, docs)

        vector_results = []
        query_emb = await self.embed(query)
        if query_emb:
            vector_results = await self._vector_search(query_emb, docs)

        if vector_results:
            fused = self._rrf_fusion([bm25_results, vector_results], k=self._rrf_k)
        else:
            fused = bm25_results

        fused.sort(key=lambda r: r.score, reverse=True)
        return fused[:top_k]

    def _load_all_docs(self) -> List[Dict[str, Any]]:
        if not self.memory_dir.exists():
            return []
        docs = []
        for f in sorted(self.memory_dir.glob("*.md")):
            if f.name.startswith("."):
                continue
            content = f.read_text(encoding="utf-8")
            date_str = f.stem
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                date = datetime.now()
            chunks = re.split(r"\n## Session: ", content)
            for i, chunk in enumerate(chunks):
                if chunk.strip():
                    chunk_with_header = f"## Session: {chunk}" if i > 0 else chunk
                    docs.append({
                        "chunk": chunk_with_header.strip(),
                        "doc_path": str(f),
                        "date": date,
                    })
        self._total_docs = len(docs)
        return docs

    def _build_bm25_index(self, docs: List[Dict[str, Any]]) -> None:
        doc_count = len(docs)
        term_freq: Counter = Counter()
        for doc in docs:
            tokens = self._tokenize(doc["chunk"])
            unique_tokens = set(tokens)
            for t in unique_tokens:
                term_freq[t] += 1
        self._bm25_doc_freq = dict(term_freq)
        total_len = sum(len(self._tokenize(d["chunk"])) for d in docs)
        self._bm25_avgdl = total_len / doc_count if doc_count > 0 else 0

    def _tokenize(self, text: str) -> List[str]:
        tokens = text.lower().split()
        if len(tokens) == 1:
            chars = list(text.lower())
            return [chars[i] + chars[i + 1] for i in range(len(chars) - 1)]
        return tokens

    def _bm25_score(self, query: str, doc: Dict[str, Any]) -> float:
        doc_text = doc["chunk"] if isinstance(doc, dict) else doc
        tokens = self._tokenize(doc_text)
        tf = Counter(tokens)
        query_tokens = self._tokenize(query)
        score = 0.0
        doc_len = len(tokens)
        avgdl = self._bm25_avgdl if self._bm25_avgdl > 0 else 1.0
        for term in query_tokens:
            if term not in tf:
                continue
            n = self._bm25_doc_freq.get(term, 0)
            if n == 0:
                n = 1
            N = max(1, self._total_docs)
            idf = math.log((N - n + 0.5) / (n + 0.5) + 1)
            tf_val = tf[term]
            tf_component = (tf_val * (self._bm25_k1 + 1)) / (
                tf_val + self._bm25_k1 * (1 - self._bm25_b + self._bm25_b * doc_len / avgdl)
            )
            score += idf * tf_component
        return score

    def _bm25_search(self, query: str, docs: List[Dict[str, Any]]) -> List[SearchResult]:
        results = []
        for doc in docs:
            score = self._bm25_score(query, doc)
            if score > 0:
                score = self._apply_temporal_decay(score, doc["date"])
                results.append(SearchResult(chunk=doc["chunk"][:200], score=score, doc_path=doc["doc_path"], date=doc["date"]))
        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def _vector_score(self, query_emb: List[float], doc_emb: List[float]) -> float:
        if not query_emb or not doc_emb or len(query_emb) != len(doc_emb):
            return 0.0
        dot = sum(a * b for a, b in zip(query_emb, doc_emb))
        norm_q = math.sqrt(sum(a * a for a in query_emb))
        norm_d = math.sqrt(sum(a * a for a in doc_emb))
        if norm_q == 0 or norm_d == 0:
            return 0.0
        return dot / (norm_q * norm_d)

    async def _vector_search(self, query_emb: List[float], docs: List[Dict[str, Any]]) -> List[SearchResult]:
        results = []
        for doc in docs:
            cache_key = f"{doc['doc_path']}:{hash(doc['chunk'][:100])}"
            if cache_key in self._embedding_cache:
                doc_emb = self._embedding_cache[cache_key]
            else:
                doc_emb = await self.embed(doc["chunk"][:500])
                if doc_emb:
                    self._embedding_cache[cache_key] = doc_emb
                else:
                    continue
            score = self._vector_score(query_emb, doc_emb)
            if score > 0:
                score = self._apply_temporal_decay(score, doc["date"])
                results.append(SearchResult(chunk=doc["chunk"][:200], score=score, doc_path=doc["doc_path"], date=doc["date"]))
        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def _rrf_fusion(self, rankings: List[List[SearchResult]], k: int = 60) -> List[SearchResult]:
        rrf_scores: Dict[str, float] = {}
        chunk_to_result: Dict[str, SearchResult] = {}

        for ranking in rankings:
            for rank, result in enumerate(ranking):
                chunk_key = f"{result.doc_path}:{result.chunk[:50]}"
                if chunk_key not in rrf_scores:
                    rrf_scores[chunk_key] = 0.0
                    chunk_to_result[chunk_key] = result
                rrf_scores[chunk_key] += 1.0 / (k + rank + 1)

        fused = [
            SearchResult(
                chunk=chunk_to_result[k].chunk,
                score=rrf_scores[k],
                doc_path=chunk_to_result[k].doc_path,
                date=chunk_to_result[k].date,
            )
            for k in rrf_scores
        ]
        fused.sort(key=lambda r: r.score, reverse=True)
        return fused

    def _apply_temporal_decay(self, score: float, doc_date: Optional[datetime]) -> float:
        if not doc_date:
            return score
        now = datetime.now()
        age_days = (now - doc_date).days
        if age_days <= 0:
            return score
        decay_factor = max(0.5, 1.0 - (age_days / self._temporal_decay_days))
        return score * decay_factor