# RAG 混合检索系统设计

**日期**: 2026-03-31
**状态**: 已确认
**目标**: 为历史会话日志实现轻量级 RAG 检索

---

## 1. 背景与目标

MEMORY.md 已全量注入 System Prompt，但历史会话日志（`app/memory/logs/*.md`）未建立检索机制。当用户问及历史行程、偏好推断、跨会话上下文时，系统无法高效检索相关内容。

**使用场景**:
- 历史行程问答: "上次去杭州行程是怎样的？"
- 偏好推断: 从历史中推断用户未明说的偏好
- 跨会话上下文: 连续多天规划时关联前一天方案

**设计原则**: 轻量优先，BM25 + 简单向量混合检索，零额外外部依赖。

---

## 2. 检索架构

### 2.1 整体流程

```
用户消息
    │
    ▼
┌──────────────────────────────────────────────┐
│            HybridRetriever                    │
│                                              │
│  ┌─────────────┐    ┌─────────────────────┐ │
│  │ BM25 检索   │    │ Simple Vector 检索  │ │
│  │ (关键词)    │    │ (词频向量化)        │ │
│  └──────┬──────┘    └──────────┬──────────┘ │
│         │                       │            │
│         └───────┬───────────────┘            │
│                 ▼                             │
│          RRF 融合排序                         │
│                 │                            │
│         Top-k 结果                           │
└──────────────────────────────────────────────┘
    │
    ▼
注入到 MemoryInjector
```

### 2.2 组件职责

| 组件 | 文件 | 职责 |
|------|------|------|
| `SearchIndexer` | `app/services/memory/search_indexer.py` | 解析日志，建立 BM25 倒排索引和向量库 |
| `HybridRetriever` | `app/services/memory/hybrid_retriever.py` | BM25 + 向量双路检索，RRF 融合 |
| `MemorySearchService` | `app/services/memory/search_service.py` | 对外接口 `search(query, user_id, top_k)` |

---

## 3. 数据结构

### 3.1 日志切分

每个会话消息对（Human + AI）为一个检索文档：

```python
class LogDocument:
    doc_id: str          # "log_2026-03-28_001"
    date: str            # "2026-03-28"
    session_id: str      # 会话标识
    human_message: str    # 用户输入
    ai_response: str     # AI 回复
    bm25_text: str       # 分词后的文本（空格分隔）
    vector: List[float]  # 简单词频向量
```

### 3.2 索引结构

```python
class SearchIndex:
    documents: Dict[str, LogDocument]      # doc_id -> 文档
    bm25_index: Dict[str, List[str]]        # term -> [doc_id, ...]
    vector_store: List[Tuple[str, List[float]]]  # [(doc_id, vector), ...]

    # BM25 参数
    k1: float = 1.5
    b: float = 0.75
    avg_doc_len: float
```

---

## 4. 检索算法

### 4.1 BM25 检索

使用经典 BM25F 公式:

```
BM25(d, q) = Σ IDF(t) × (tf(t,d) × (k1 + 1)) / (tf(t,d) + k1 × (1 - b + b × |d| / avgdl))
```

分词采用简单中文分词（基于字符 n-gram + 停用词过滤）。

### 4.2 简单向量检索

采用词频向量（TF-IDF 简化版）:

```python
def compute_vector(text: str, vocab: List[str]) -> List[float]:
    tokens = tokenize(text)
    freq = Counter(tokens)
    vector = [freq.get(word, 0) for word in vocab]
    # L2 归一化
    norm = sqrt(sum(v * v for v in vector))
    return [v / norm if norm > 0 else 0 for v in vector]
```

相似度使用余弦相似度。

### 4.3 RRF 融合

Reciprocal Rank Fusion 融合多路检索结果:

```
RRF_score(d) = Σ 1 / (k + rank_i(d))
```

其中 k=60（默认），rank_i(d) 为第 i 路检索中文档 d 的排名。

---

## 5. 索引更新策略

**每日定时批量索引**:

- 每日凌晨（或首次调用时）检查日志目录
- 仅索引上次索引后新增/修改的日志文件
- 索引结果存储在内存中（应用重启时重新构建）
- 可通过 API 手动触发重建索引

---

## 6. 集成方式

### 6.1 MemoryInjector 改造

`MemoryInjector.load_session_memory()` 增加 RAG 检索参数:

```python
async def load_session_memory(
    self,
    user_id: str,
    session_id: str,
    mode: Literal["main", "shared"] = "main",
    query: Optional[str] = None,  # 新增：用于 RAG 检索
) -> str:
    parts = []

    # 现有逻辑：日志（今日+昨日）+ MEMORY.md
    ...

    # 新增：RAG 检索历史日志
    if query:
        rag_results = await self.search_service.search(
            query=query,
            user_id=user_id,
            top_k=3
        )
        if rag_results:
            parts.append(f"## 相关历史会话\n\n{rag_results}")

    return "\n\n".join(parts)
```

### 6.2 调用入口

在 `ChatService.chat()` 中，调用 `MemoryInjector` 时传入当前用户消息作为 query。

---

## 7. 文件结构

```
app/services/memory/
├── __init__.py
├── markdown_memory.py      # 现有，不改
├── session_manager.py      # 现有，不改
├── daily_log.py            # 现有，不改
├── memory_injector.py      # 改造：集成 RAG
├── search_indexer.py       # 新增：BM25 + 向量索引
├── hybrid_retriever.py     # 新增：混合检索器
└── search_service.py       # 新增：对外服务接口
```

---

## 8. API 设计

### 8.1 检索接口

```python
# app/services/memory/search_service.py
class MemorySearchService:
    async def search(
        self,
        query: str,
        user_id: str,
        top_k: int = 3,
    ) -> str:
        """检索相关历史会话，返回格式化字符串。"""
```

### 8.2 管理接口（可选）

```bash
POST /api/memory/reindex    # 手动触发重建索引
GET  /api/memory/stats      # 查看索引统计信息
```

---

## 9. 错误处理

| 场景 | 处理方式 |
|------|----------|
| 索引不存在 | 首次检索时自动构建索引 |
| 检索服务异常 | 降级：返回空结果，不阻塞主流程 |
| 无相关结果 | 返回空字符串，不注入历史会话 |
| 日志文件读取失败 | 跳过该文件，记录 warning 日志 |

---

## 10. 测试策略

- 单元测试: BM25 计算、向量化、RRF 融合
- 集成测试: 完整检索流程 + 注入到 MemoryInjector
- 边界测试: 空查询、无索引、文件不存在

---

## 11. 后续扩展

如需增强语义理解，可平滑升级为 Ollama Embedding 或云 API Embedding，仅需替换 `compute_vector()` 实现。
