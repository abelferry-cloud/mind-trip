# RAG 混合检索系统实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为历史会话日志实现 BM25 + 简单向量混合检索系统，支持 RRF 融合排序和每日批量索引。

**Architecture:** 三个核心组件：SearchIndexer（索引）、HybridRetriever（检索）、MemorySearchService（服务）。MemoryInjector 改造后支持 RAG 查询。全部 in-memory 存储，无外部依赖。

**Tech Stack:** 纯 Python（标准库 + math），无外部向量库依赖。

---

## 文件结构

```
app/services/memory/
├── __init__.py                    # 改造：导出新增组件
├── memory_injector.py             # 改造：集成 RAG 查询
├── search_indexer.py               # 新增：BM25 + 向量索引
├── hybrid_retriever.py            # 新增：混合检索 + RRF
└── search_service.py              # 新增：对外服务接口

tests/services/
└── test_memory_search.py          # 新增：检索系统测试
```

---

## Task 1: 创建 LogDocument 数据结构

**Files:**
- Create: `app/services/memory/search_indexer.py`

- [ ] **Step 1: 写测试**

```python
# tests/services/test_memory_search.py
from app.services.memory.search_indexer import LogDocument

def test_log_document_creation():
    doc = LogDocument(
        doc_id="log_2026-03-28_001",
        date="2026-03-28",
        session_id="abc123",
        human_message="我想去杭州3天",
        ai_response="已为您规划杭州3天行程..."
    )
    assert doc.doc_id == "log_2026-03-28_001"
    assert doc.date == "2026-03-28"
    assert "杭州" in doc.human_message
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `pytest tests/services/test_memory_search.py::test_log_document_creation -v`
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: 实现 LogDocument**

```python
# app/services/memory/search_indexer.py
"""SearchIndexer - BM25 + 简单向量索引器。"""
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import re
from collections import Counter
import math


@dataclass
class LogDocument:
    """日志检索文档：每个 Human+AI 消息对为一个文档。"""
    doc_id: str
    date: str
    session_id: str
    human_message: str
    ai_response: str
    bm25_text: str = ""
    vector: List[float] = field(default_factory=list)

    def __post_init__(self):
        if not self.bm25_text:
            self.bm25_text = self._build_bm25_text()

    def _build_bm25_text(self) -> str:
        combined = f"{self.human_message} {self.ai_response}"
        tokens = simple_tokenize(combined)
        return " ".join(tokens)


def simple_tokenize(text: str) -> List[str]:
    """简单中文分词：字符 n-gram + 停用词过滤。"""
    # 停用词
    stopwords = {"的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这"}
    # 字符级分词（2-gram）
    chars = list(text)
    tokens = []
    for i in range(len(chars) - 1):
        bigram = chars[i] + chars[i + 1]
        if bigram not in stopwords and not bigram.strip() == "":
            tokens.append(bigram)
    return tokens
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `pytest tests/services/test_memory_search.py::test_log_document_creation -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add app/services/memory/search_indexer.py tests/services/test_memory_search.py
git commit -m "feat(memory): add LogDocument and simple_tokenize for search indexer"
```

---

## Task 2: 实现 BM25 索引和检索

**Files:**
- Modify: `app/services/memory/search_indexer.py`

- [ ] **Step 1: 写测试**

```python
# tests/services/test_memory_search.py
import pytest

def test_bm25_idf_calculation(search_indexer):
    # "杭州" 在 3 个文档中出现，IDF 应该 > 0
    idf = search_indexer._compute_idf("杭州")
    assert idf > 0

def test_bm25_score_positive(search_indexer, sample_doc):
    query = "杭州 旅行"
    score = search_indexer.bm25_score(query, sample_doc)
    assert score >= 0

def test_bm25_search_returns_ranked_results(search_indexer, three_docs):
    results = search_indexer.bm25_search("杭州 3天", top_k=2)
    assert len(results) <= 2
    # 结果应该按分数降序
    if len(results) >= 2:
        assert results[0][1] >= results[1][1]
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `pytest tests/services/test_memory_search.py::test_bm25_idf_calculation -v`
Expected: FAIL - AttributeError: 'SearchIndexer' object has no attribute '_compute_idf'

- [ ] **Step 3: 实现 SearchIndexer 类**

在 `search_indexer.py` 中添加：

```python
class SearchIndexer:
    """BM25 + 简单向量混合索引器。"""

    def __init__(self, memory_dir: Optional[Path] = None):
        if memory_dir is None:
            memory_dir = Path(__file__).parent.parent.parent / "memory" / "logs"
        self.memory_dir = Path(memory_dir)
        self.documents: Dict[str, LogDocument] = {}
        self.bm25_index: Dict[str, List[str]] = {}  # term -> [doc_id, ...]
        self.vector_vocab: List[str] = []
        self.vector_store: List[Tuple[str, List[float]]] = []  # [(doc_id, vector), ...]
        self.k1: float = 1.5
        self.b: float = 0.75
        self.avg_doc_len: float = 0.0
        self._num_docs: int = 0

    def _compute_idf(self, term: str) -> float:
        """计算 IDF。"""
        doc_count = sum(1 for doc in self.documents.values() if term in doc.bm25_text)
        if doc_count == 0:
            return 0.0
        return math.log((self._num_docs - doc_count + 0.5) / (doc_count + 0.5) + 1)

    def bm25_score(self, query: str, doc: LogDocument) -> float:
        """计算单个文档的 BM25 分数。"""
        tokens = simple_tokenize(query)
        doc_len = len(doc.bm25_text.split())
        score = 0.0
        for token in tokens:
            tf = doc.bm25_text.count(token)
            if tf > 0:
                idf = self._compute_idf(token)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / max(self.avg_doc_len, 1))
                score += idf * numerator / denominator
        return score

    def bm25_search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """BM25 检索，返回 [(doc_id, score), ...]"""
        scores = []
        for doc_id, doc in self.documents.items():
            score = self.bm25_score(query, doc)
            if score > 0:
                scores.append((doc_id, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `pytest tests/services/test_memory_search.py::test_bm25_idf_calculation tests/services/test_memory_search.py::test_bm25_score_positive tests/services/test_memory_search.py::test_bm25_search_returns_ranked_results -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add app/services/memory/search_indexer.py tests/services/test_memory_search.py
git commit -m "feat(memory): add SearchIndexer with BM25 scoring"
```

---

## Task 3: 实现向量检索

**Files:**
- Modify: `app/services/memory/search_indexer.py`

- [ ] **Step 1: 写测试**

```python
# tests/services/test_memory_search.py

def test_vector_compute_normalized(search_indexer):
    text = "杭州旅行 3天"
    vector = search_indexer.compute_vector(text)
    # 应该 L2 归一化
    norm = math.sqrt(sum(v * v for v in vector))
    assert abs(norm - 1.0) < 0.001

def test_vector_search_returns_ranked_results(search_indexer, three_docs):
    results = search_indexer.vector_search("杭州", top_k=2)
    assert len(results) <= 2
    if len(results) >= 2:
        assert results[0][1] >= results[1][1]  # 余弦相似度降序
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `pytest tests/services/test_memory_search.py::test_vector_compute_normalized -v`
Expected: FAIL - AttributeError

- [ ] **Step 3: 实现向量方法**

在 `SearchIndexer` 类中添加：

```python
    def _build_vocabulary(self) -> None:
        """从所有文档构建词表。"""
        all_tokens = set()
        for doc in self.documents.values():
            all_tokens.update(doc.bm25_text.split())
        self.vector_vocab = sorted(list(all_tokens))

    def compute_vector(self, text: str) -> List[float]:
        """计算 L2 归一化词频向量。"""
        tokens = simple_tokenize(text)
        freq = Counter(tokens)
        vector = [freq.get(word, 0) for word in self.vector_vocab]
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]
        return vector

    def vector_search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """向量相似度检索，返回 [(doc_id, cosine_similarity), ...]"""
        query_vec = self.compute_vector(query)
        scores = []
        for doc_id, doc_vec in self.vector_store:
            score = self._cosine_similarity(query_vec, doc_vec)
            if score > 0:
                scores.append((doc_id, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度。"""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        return dot  # 已归一化
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `pytest tests/services/test_memory_search.py::test_vector_compute_normalized tests/services/test_memory_search.py::test_vector_search_returns_ranked_results -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add app/services/memory/search_indexer.py tests/services/test_memory_search.py
git commit -m "feat(memory): add vector similarity search to SearchIndexer"
```

---

## Task 4: 实现索引构建（从日志文件）

**Files:**
- Modify: `app/services/memory/search_indexer.py`

- [ ] **Step 1: 写测试**

```python
# tests/services/test_memory_search.py

def test_index_logs_from_directory(tmp_path):
    # 创建临时日志目录
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    # 创建测试日志文件
    log_file = log_dir / "2026-03-28.md"
    log_file.write_text("""# 2026-03-28

## Session: session001

[20:45:33]
Human: 我想去杭州3天
AI: 已为您规划杭州3天行程...
""", encoding="utf-8")

    indexer = SearchIndexer(memory_dir=log_dir)
    indexer.build_index()

    assert len(indexer.documents) == 1
    doc = list(indexer.documents.values())[0]
    assert "杭州" in doc.human_message

def test_build_index_skips_malformed_files(tmp_path, caplog):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    bad_file = log_dir / "2026-03-28.md"
    bad_file.write_text("not valid markdown", encoding="utf-8")

    indexer = SearchIndexer(memory_dir=log_dir)
    indexer.build_index()  # 不应抛异常

    assert "warning" in caplog.text.lower() or len(indexer.documents) == 0
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `pytest tests/services/test_memory_search.py::test_index_logs_from_directory -v`
Expected: FAIL - build_index not implemented

- [ ] **Step 3: 实现日志解析和 build_index**

在 `SearchIndexer` 类中添加：

```python
    def build_index(self) -> None:
        """扫描日志目录，构建 BM25 索引和向量库。"""
        if not self.memory_dir.exists():
            return

        self.documents.clear()
        self.bm25_index.clear()
        self.vector_store.clear()

        doc_counter = 0
        for log_file in sorted(self.memory_dir.glob("*.md")):
            try:
                self._parse_log_file(log_file, doc_counter)
                doc_counter = len(self.documents)
            except Exception as e:
                import logging
                logging.warning(f"Failed to parse {log_file}: {e}")

        self._num_docs = len(self.documents)
        self._build_vocabulary()
        self._build_vector_store()
        self.avg_doc_len = sum(len(d.bm25_text.split()) for d in self.documents.values()) / max(self._num_docs, 1)

    def _parse_log_file(self, log_file: Path, start_counter: int) -> None:
        """解析单个日志文件，提取 Human/AI 消息对。"""
        content = log_file.read_text(encoding="utf-8")
        date_str = log_file.stem  # "2026-03-28"

        # 匹配 Human: ... AI: ... 消息对
        pattern = r"## Session: (\S+).*?\[(\d+:\d+:\d+)\]\s*Human: (.+?)\s*AI: (.+?)(?=\n## Session: |\n\[|\Z)"
        for match in re.finditer(pattern, content, re.DOTALL):
            session_id = match.group(1)
            timestamp = match.group(2)
            human_msg = match.group(3).strip()
            ai_msg = match.group(4).strip()

            doc_id = f"log_{date_str}_{start_counter:03d}"
            start_counter += 1

            doc = LogDocument(
                doc_id=doc_id,
                date=date_str,
                session_id=session_id,
                human_message=human_msg,
                ai_response=ai_msg,
            )
            self.documents[doc_id] = doc

            # BM25 倒排索引
            for token in doc.bm25_text.split():
                if token not in self.bm25_index:
                    self.bm25_index[token] = []
                self.bm25_index[token].append(doc_id)

    def _build_vector_store(self) -> None:
        """为所有文档预计算向量。"""
        self.vector_store = []
        for doc_id, doc in self.documents.items():
            doc.vector = self.compute_vector(doc.bm25_text)
            self.vector_store.append((doc_id, doc.vector))
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `pytest tests/services/test_memory_search.py::test_index_logs_from_directory tests/services/test_memory_search.py::test_build_index_skips_malformed_files -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add app/services/memory/search_indexer.py tests/services/test_memory_search.py
git commit -m "feat(memory): add build_index to parse log files into documents"
```

---

## Task 5: 创建 HybridRetriever（RRF 融合）

**Files:**
- Create: `app/services/memory/hybrid_retriever.py`

- [ ] **Step 1: 写测试**

```python
# tests/services/test_memory_search.py
from app.services.memory.hybrid_retriever import HybridRetriever

def test_rrf_fusion_ranks_by_combined_score(search_indexer):
    retriever = HybridRetriever(search_indexer)
    # BM25 返回 [(doc1, 10), (doc2, 5)]
    # Vector 返回 [(doc2, 0.9), (doc3, 0.8)]
    bm25_results = [("doc1", 10.0), ("doc2", 5.0)]
    vector_results = [("doc2", 0.9), ("doc3", 0.8)]

    fused = retriever._rrf_fusion(bm25_results, vector_results, k=60)
    doc_ids = [doc_id for doc_id, _ in fused]

    # doc2 在两路都出现，应该排第一
    assert doc_ids[0] == "doc2"

def test_hybrid_search_combines_both_paths(search_indexer):
    retriever = HybridRetriever(search_indexer)
    search_indexer.documents = {
        "doc1": LogDocument("doc1", "2026-03-28", "s1", "杭州", "规划完成"),
        "doc2": LogDocument("doc2", "2026-03-28", "s1", "北京", "行程安排"),
    }
    search_indexer._num_docs = 2
    search_indexer.vector_vocab = ["杭州", "北京"]
    search_indexer.avg_doc_len = 1.0
    search_indexer._build_vector_store()

    results = retriever.hybrid_search("杭州", top_k=2)
    assert len(results) >= 1
    assert results[0][0] == "doc1"
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `pytest tests/services/test_memory_search.py::test_rrf_fusion_ranks_by_combined_score -v`
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: 实现 HybridRetriever**

```python
# app/services/memory/hybrid_retriever.py
"""HybridRetriever - BM25 + 向量混合检索，RRF 融合。"""
from typing import List, Tuple, Optional, Dict
from app.services.memory.search_indexer import SearchIndexer


class HybridRetriever:
    """混合检索器：BM25 + 向量 + RRF 融合。"""

    def __init__(self, indexer: SearchIndexer, rrf_k: int = 60):
        self.indexer = indexer
        self.rrf_k = rrf_k

    def hybrid_search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """混合检索：BM25 + 向量，然后 RRF 融合。"""
        bm25_results = self.indexer.bm25_search(query, top_k=top_k * 2)
        vector_results = self.indexer.vector_search(query, top_k=top_k * 2)

        if not bm25_results and not vector_results:
            return []
        if not bm25_results:
            return vector_results[:top_k]
        if not vector_results:
            return bm25_results[:top_k]

        return self._rrf_fusion(bm25_results, vector_results, k=self.rrf_k)[:top_k]

    def _rrf_fusion(
        self,
        bm25_results: List[Tuple[str, float]],
        vector_results: List[Tuple[str, float]],
        k: int = 60,
    ) -> List[Tuple[str, float]]:
        """Reciprocal Rank Fusion 融合多路检索结果。"""
        rrf_scores: Dict[str, float] = {}

        # BM25 排名
        for rank, (doc_id, _) in enumerate(bm25_results, 1):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank)

        # Vector 排名
        for rank, (doc_id, _) in enumerate(vector_results, 1):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank)

        sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_results
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `pytest tests/services/test_memory_search.py::test_rrf_fusion_ranks_by_combined_score tests/services/test_memory_search.py::test_hybrid_search_combines_both_paths -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add app/services/memory/hybrid_retriever.py tests/services/test_memory_search.py
git commit -m "feat(memory): add HybridRetriever with RRF fusion"
```

---

## Task 6: 创建 MemorySearchService 对外接口

**Files:**
- Create: `app/services/memory/search_service.py`

- [ ] **Step 1: 写测试**

```python
# tests/services/test_memory_search.py
from app.services.memory.search_service import MemorySearchService

@pytest.fixture
def search_service(tmp_path):
    # 创建临时日志
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    log_file = log_dir / "2026-03-28.md"
    log_file.write_text("""# 2026-03-28

## Session: sess001

[20:45:33]
Human: 我想去杭州3天
AI: 已为您规划杭州行程，预算3000元
""", encoding="utf-8")

    service = MemorySearchService(memory_dir=str(log_dir))
    return service

def test_search_returns_formatted_string(search_service):
    result = search_service.search("杭州", user_id="user1", top_k=1)
    assert "杭州" in result
    assert "2026-03-28" in result

def test_search_empty_query_returns_empty(search_service):
    result = search_service.search("", user_id="user1", top_k=3)
    assert result == ""

def test_service_lazy_indexing(search_service):
    # 首次搜索时才构建索引
    assert search_service.indexer._num_docs == 0
    search_service.search("杭州", user_id="user1")
    assert search_service.indexer._num_docs == 1
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `pytest tests/services/test_memory_search.py::test_search_returns_formatted_string -v`
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: 实现 MemorySearchService**

```python
# app/services/memory/search_service.py
"""MemorySearchService - 对外 RAG 检索服务接口。"""
from typing import Optional
from pathlib import Path
from app.services.memory.search_indexer import SearchIndexer
from app.services.memory.hybrid_retriever import HybridRetriever


class MemorySearchService:
    """RAG 检索服务：整合索引、检索、格式化输出。"""

    def __init__(self, memory_dir: Optional[str] = None):
        if memory_dir is None:
            memory_dir = Path(__file__).parent.parent.parent / "memory" / "logs"
        else:
            memory_dir = Path(memory_dir)
        self.indexer = SearchIndexer(memory_dir=memory_dir)
        self.retriever = HybridRetriever(self.indexer)
        self._index_built = False

    def _ensure_index(self) -> None:
        """懒加载索引。"""
        if not self._index_built:
            self.indexer.build_index()
            self._index_built = True

    async def search(
        self,
        query: str,
        user_id: str,
        top_k: int = 3,
    ) -> str:
        """检索相关历史会话，返回格式化 Markdown 字符串。"""
        if not query or not query.strip():
            return ""

        try:
            self._ensure_index()

            results = self.retriever.hybrid_search(query, top_k=top_k)
            if not results:
                return ""

            parts = []
            for doc_id, score in results:
                doc = self.indexer.documents.get(doc_id)
                if not doc:
                    continue
                parts.append(
                    f"> **日期**: {doc.date} | **Session**: {doc.session_id}\n"
                    f"> **Human**: {doc.human_message[:100]}{'...' if len(doc.human_message) > 100 else ''}\n"
                    f"> **AI**: {doc.ai_response[:150]}{'...' if len(doc.ai_response) > 150 else ''}"
                )

            return "\n\n".join(parts)

        except Exception:
            # 降级：检索失败时返回空字符串
            return ""
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `pytest tests/services/test_memory_search.py::test_search_returns_formatted_string tests/services/test_memory_search.py::test_search_empty_query_returns_empty tests/services/test_memory_search.py::test_service_lazy_indexing -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add app/services/memory/search_service.py tests/services/test_memory_search.py
git commit -m "feat(memory): add MemorySearchService with async search interface"
```

---

## Task 7: 集成到 MemoryInjector

**Files:**
- Modify: `app/services/memory/memory_injector.py`
- Modify: `app/services/memory/__init__.py`

- [ ] **Step 1: 写测试**

```python
# tests/services/test_memory_search.py

@pytest.mark.asyncio
async def test_memory_injector_calls_search_service(tmp_path):
    # 创建临时日志
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    log_file = log_dir / "2026-03-28.md"
    log_file.write_text("""# 2026-03-28

## Session: sess001

[20:45:33]
Human: 我想去杭州
AI: 已规划
""", encoding="utf-8")

    injector = MemoryInjector(memory_dir=str(tmp_path / "memory"))
    # 需要 MEMORY.md
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory" / "MEMORY.md").write_text("# MEMORY.md\n\n## User Profile\n\n- **Name**: Test", encoding="utf-8")

    result = await injector.load_session_memory(
        user_id="user1",
        session_id="sess001",
        mode="main",
        query="杭州",
    )

    assert "相关历史会话" in result or "杭州" in result
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `pytest tests/services/test_memory_search.py::test_memory_injector_calls_search_service -v`
Expected: FAIL - AttributeError: 'MemoryInjector' has no attribute 'search_service'

- [ ] **Step 3: 改造 MemoryInjector**

```python
# app/services/memory/memory_injector.py
# 在 __init__ 中添加:
from app.services.memory.search_service import MemorySearchService

class MemoryInjector:
    def __init__(self, ...):
        # ... 现有初始化 ...
        self.search_service = MemorySearchService()

    async def load_session_memory(...):
        # 在方法末尾添加:
        if query:
            rag_results = await self.search_service.search(
                query=query,
                user_id=user_id,
                top_k=3,
            )
            if rag_results:
                parts.append(f"## 相关历史会话\n\n{rag_results}")
```

具体修改 `load_session_memory` 方法:

```python
    async def load_session_memory(
        self,
        user_id: str,
        session_id: str,
        mode: Literal["main", "shared"] = "main",
        query: Optional[str] = None,
    ) -> str:
        parts = []

        # 日志（今日 + 昨日）— 始终加载
        daily_content = self.daily_log_manager.read_today_and_yesterday()
        if daily_content:
            parts.append(f"## 今日与昨日会话日志\n\n{daily_content}")

        # 长期记忆 — 仅在 main 私有会话中
        if mode == "main":
            memory_content = self.memory_manager.get_memory()
            if memory_content:
                parts.append(f"## 长期记忆 (MEMORY.md)\n\n{memory_content}")

        # RAG 检索历史日志
        if query:
            try:
                rag_results = await self.search_service.search(
                    query=query,
                    user_id=user_id,
                    top_k=3,
                )
                if rag_results:
                    parts.append(f"## 相关历史会话\n\n{rag_results}")
            except Exception:
                pass  # 降级：RAG 失败不影响主流程

        return "\n\n".join(parts) if parts else ""
```

- [ ] **Step 4: 更新 __init__.py 导出**

```python
# app/services/memory/__init__.py
from app.services.memory.search_service import (
    MemorySearchService,
    get_memory_search_service,
)
from app.services.memory.search_indexer import SearchIndexer
from app.services.memory.hybrid_retriever import HybridRetriever

__all__ = [
    # ... existing exports ...
    "MemorySearchService",
    "get_memory_search_service",
    "SearchIndexer",
    "HybridRetriever",
]
```

在 `search_service.py` 添加单例:

```python
_search_service: Optional["MemorySearchService"] = None

def get_memory_search_service() -> "MemorySearchService":
    global _search_service
    if _search_service is None:
        _search_service = MemorySearchService()
    return _search_service
```

- [ ] **Step 5: 运行测试，确认通过**

Run: `pytest tests/services/test_memory_search.py::test_memory_injector_calls_search_service -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add app/services/memory/memory_injector.py app/services/memory/__init__.py app/services/memory/search_service.py tests/services/test_memory_search.py
git commit -m "feat(memory): integrate RAG search into MemoryInjector"
```

---

## Task 8: 改造 ChatService 传入 query

**Files:**
- Modify: `app/services/chat/chat_service.py`

- [ ] **Step 1: 写测试**

```python
# tests/services/test_memory_search.py

@pytest.mark.asyncio
async def test_chat_service_passes_query_to_injector():
    from app.services.chat.chat_service import ChatService
    from unittest.mock import AsyncMock, patch

    service = ChatService()

    with patch.object(service._injector, 'load_session_memory', new_callable=AsyncMock) as mock_load:
        mock_load.return_value = "memory content"
        await service.chat(user_id="u1", session_id="s1", message="上次去杭州怎样")

        # 验证 load_session_memory 被调用时传入了 query
        mock_load.assert_called_once()
        call_kwargs = mock_load.call_args.kwargs
        assert "query" in call_kwargs
        assert "杭州" in call_kwargs["query"]
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `pytest tests/services/test_memory_search.py::test_chat_service_passes_query_to_injector -v`
Expected: FAIL - ChatService doesn't pass query

- [ ] **Step 3: 修改 ChatService.chat()**

在 `chat_service.py` 的 `chat()` 方法中，找到：

```python
        session_memory = await self._injector.load_session_memory(
            user_id=user_id,
            session_id=session_id,
            mode="main",
        )
```

改为：

```python
        session_memory = await self._injector.load_session_memory(
            user_id=user_id,
            session_id=session_id,
            mode="main",
            query=message,  # 传入用户消息用于 RAG 检索
        )
```

同样更新 `chat_stream()` 方法中的调用（如果使用 MemoryInjector）。

- [ ] **Step 4: 运行测试，确认通过**

Run: `pytest tests/services/test_memory_search.py::test_chat_service_passes_query_to_injector -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add app/services/chat/chat_service.py tests/services/test_memory_search.py
git commit -m "feat(chat): pass user message as query for RAG retrieval"
```

---

## Task 9: 添加 pytest fixtures 和清理

**Files:**
- Modify: `tests/services/test_memory_search.py`

- [ ] **Step 1: 添加 conftest.py 的 fixtures**

```python
# tests/services/conftest.py
import pytest
import sys
from pathlib import Path

# 确保 app 在 path 中
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

@pytest.fixture
def search_indexer(tmp_path):
    from app.services.memory.search_indexer import SearchIndexer
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return SearchIndexer(memory_dir=log_dir)

@pytest.fixture
def sample_doc():
    from app.services.memory.search_indexer import LogDocument
    return LogDocument(
        doc_id="doc1",
        date="2026-03-28",
        session_id="sess1",
        human_message="我想去杭州3天",
        ai_response="已为您规划杭州3天行程...",
    )

@pytest.fixture
def three_docs(search_indexer):
    from app.services.memory.search_indexer import LogDocument
    docs = [
        LogDocument("doc1", "2026-03-28", "s1", "杭州 旅行", "规划完成"),
        LogDocument("doc2", "2026-03-28", "s1", "北京 旅游", "行程安排"),
        LogDocument("doc3", "2026-03-29", "s2", "上海 出差", "商务行程"),
    ]
    for doc in docs:
        search_indexer.documents[doc.doc_id] = doc
    search_indexer._num_docs = len(docs)
    search_indexer._build_vocabulary()
    search_indexer.avg_doc_len = 2.0
    search_indexer._build_vector_store()
    return docs
```

- [ ] **Step 2: 运行完整测试套件**

Run: `pytest tests/services/test_memory_search.py -v`
Expected: 全部 PASS

- [ ] **Step 3: 提交**

```bash
git add tests/services/conftest.py tests/services/test_memory_search.py
git commit -m "test(memory): add pytest fixtures and complete test suite"
```

---

## 实现顺序总结

| Task | 组件 | 依赖 |
|------|------|------|
| 1 | LogDocument + simple_tokenize | 无 |
| 2 | SearchIndexer BM25 | Task 1 |
| 3 | SearchIndexer 向量 | Task 2 |
| 4 | build_index 日志解析 | Task 3 |
| 5 | HybridRetriever RRF | Task 4 |
| 6 | MemorySearchService | Task 5 |
| 7 | MemoryInjector 集成 | Task 6 |
| 8 | ChatService 改造 | Task 7 |
| 9 | 测试 fixtures | Task 1-8 |

---

## 验证命令

```bash
# 运行所有测试
pytest tests/services/test_memory_search.py -v

# 手动测试（如果日志目录存在）
python -c "
import asyncio
from app.services.memory.search_service import get_memory_search_service
async def test():
    svc = get_memory_search_service()
    result = await svc.search('杭州', user_id='test', top_k=3)
    print(result)
asyncio.run(test())
"
```
