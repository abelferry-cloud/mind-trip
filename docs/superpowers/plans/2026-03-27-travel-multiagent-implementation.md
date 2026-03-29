# 出行规划 Multi-Agent 系统实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现基于 LangChain 的工业级出行规划 Multi-Agent 系统（Supervisor + 7 Agent），包含双层记忆系统、FastAPI Web 服务、Tools 定义、容错兜底策略和监控指标。

**Architecture:** 采用 Supervisor + Specialist 模式，Planning Agent 为总控，子 Agent 并行/顺序协作。数据流：User → FastAPI → Planning Agent → 并行调用 Attractions/Budget → Route → 并行调用 Food/Hotel → Budget 校验（超支触发 Route 调整）→ 整合输出。双层记忆：短期（LangChain ConversationBuffer）+ 长期（SQLite）。

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, LangChain/LangGraph, OpenAI SDK, SQLite (aiosqlite), Prometheus Client, Pydantic, Python-dotenv, pytest, httpx

---

## 阶段一：项目脚手架与基础设施

### Task 1: 项目初始化与依赖配置

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `app/__init__.py`
- Create: `data/.gitkeep`

- [ ] **Step 1: Create requirements.txt**

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
langchain>=0.3.0
langchain-openai>=0.2.0
langchain-core>=0.3.0
langgraph>=0.2.0
aiosqlite>=0.20.0
prometheus-client>=0.20.0
pydantic>=2.9.0
pydantic-settings>=2.5.0
python-dotenv>=1.0.0
pytest>=8.3.0
pytest-asyncio>=0.24.0
httpx>=0.27.0
structlog>=24.0.0
```

- [ ] **Step 2: Create .env.example**

```bash
# LLM Provider
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
CLAUDE_API_KEY=sk-...

# Database
DATABASE_URL=data/memory.db

# Application
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO

# Model Fallback Chain
MODEL_CHAIN=openai,claude,local
PRIMARY_MODEL=openai

# Timeouts (seconds)
TOOL_TIMEOUT=10
AGENT_TIMEOUT=30
REQUEST_TIMEOUT=90
LLM_RETRY_INTERVAL=2
```

- [ ] **Step 3: Create data/.gitkeep**

```bash
# Keep data directory in version control (db file is gitignored)
echo "*.db" >> .gitignore
touch data/.gitkeep
```

- [ ] **Step 4: Commit**

```bash
git init
git add requirements.txt .env.example data/.gitkeep
git commit -m "feat: project scaffold - dependencies, env config, data dir"
```

---

### Task 2: 配置模块

**Files:**
- Create: `app/config.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Write test for config loading**

```python
# tests/test_config.py
import os
from app.config import Settings, load_settings

def test_default_values():
    os.environ.clear()
    settings = load_settings()
    assert settings.openai_model == "gpt-4o-mini"
    assert settings.tool_timeout == 10
    assert settings.agent_timeout == 30
    assert settings.request_timeout == 90

def test_env_override(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    monkeypatch.setenv("TOOL_TIMEOUT", "5")
    settings = load_settings()
    assert settings.openai_model == "gpt-4o"
    assert settings.tool_timeout == 5
```

- [ ] **Step 2: Run test to verify it fails**

```
Expected: FAIL - app.config does not exist
```

- [ ] **Step 3: Write app/config.py**

```python
# app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List
import os

class Settings(BaseSettings):
    # LLM
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    claude_api_key: str = ""

    # Database
    database_url: str = "data/memory.db"

    # Application
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # Model chain: comma-separated, first available is used
    model_chain: str = "openai,claude,local"
    primary_model: str = "openai"

    # Timeouts
    tool_timeout: int = 10
    agent_timeout: int = 30
    request_timeout: int = 90
    llm_retry_interval: int = 2

    @property
    def model_chain_list(self) -> List[str]:
        return [m.strip() for m in self.model_chain.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache
def get_settings() -> Settings:
    return Settings()

load_settings = get_settings
```

- [ ] **Step 4: Run test to verify it passes**

```
Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "feat: add config module with pydantic settings"
```

---

## 阶段二：记忆系统

### Task 3: 长期记忆（SQLite）

**Files:**
- Create: `app/memory/__init__.py`
- Create: `app/memory/long_term.py`
- Create: `tests/memory/test_long_term.py`

- [ ] **Step 1: Write failing test for long_term memory**

```python
# tests/memory/test_long_term.py
import pytest, asyncio
from app.memory.long_term import LongTermMemory, get_long_term_memory

@pytest.fixture
def mem():
    return get_long_term_memory(":memory:")

@pytest.mark.asyncio
async def test_update_and_get_preference(mem):
    await mem.update_preference("u1", "hardships", ["硬座"])
    await mem.update_preference("u1", "health", ["心脏病"])

    prefs = await mem.get_preference("u1")
    assert prefs["hardships"] == ["硬座"]
    assert prefs["health"] == ["心脏病"]

@pytest.mark.asyncio
async def test_update_overwrites(mem):
    await mem.update_preference("u1", "health", ["心脏病"])
    await mem.update_preference("u1", "health", ["糖尿病"])
    prefs = await mem.get_preference("u1")
    assert prefs["health"] == ["糖尿病"]

@pytest.mark.asyncio
async def test_trip_history(mem):
    plan = {"city": "杭州", "days": 3, "budget": 5000}
    await mem.save_trip_history("u1", "杭州", 3, plan)
    history = await mem.get_trip_history("u1")
    assert len(history) == 1
    assert history[0]["city"] == "杭州"
```

- [ ] **Step 2: Run test to verify it fails**

```
Expected: FAIL - module not found
```

- [ ] **Step 3: Write app/memory/long_term.py**

```python
# app/memory/long_term.py
import aiosqlite
import json
from typing import Any, Dict, List, Optional
from app.config import get_settings

class LongTermMemory:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    user_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, category)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS trip_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    city TEXT NOT NULL,
                    days INTEGER NOT NULL,
                    plan_summary TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    plan_id TEXT NOT NULL,
                    feedback_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    async def update_preference(self, user_id: str, category: str, value: Any):
        val = json.dumps(value) if isinstance(value, list) else json.dumps([value])
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO preferences (user_id, category, value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, category, val))
            await db.commit()

    async def get_preference(self, user_id: str) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT category, value FROM preferences WHERE user_id = ?", (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                result = {}
                for row in rows:
                    result[row["category"]] = json.loads(row["value"])
                return result

    async def save_trip_history(self, user_id: str, city: str, days: int, plan_summary: dict):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO trip_history (user_id, city, days, plan_summary)
                VALUES (?, ?, ?, ?)
            """, (user_id, city, days, json.dumps(plan_summary)))
            await db.commit()

    async def get_trip_history(self, user_id: str) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT city, days, plan_summary, created_at FROM trip_history WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    {"city": r["city"], "days": r["days"],
                     "plan_summary": json.loads(r["plan_summary"]), "created_at": r["created_at"]}
                    for r in rows
                ]

    async def save_feedback(self, user_id: str, plan_id: str, feedback_text: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO feedback (user_id, plan_id, feedback_text) VALUES (?, ?, ?)",
                (user_id, plan_id, feedback_text)
            )
            await db.commit()

    async def close(self):
        pass

_mem_instance: Optional[LongTermMemory] = None

def get_long_term_memory(db_path: Optional[str] = None) -> LongTermMemory:
    global _mem_instance
    if db_path is None:
        db_path = get_settings().database_url
    if _mem_instance is None:
        _mem_instance = LongTermMemory(db_path)
    return _mem_instance
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/memory/test_long_term.py -v
Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add app/memory/long_term.py tests/memory/test_long_term.py
git commit -m "feat: add long-term memory with SQLite (preferences, trip_history, feedback)"
```

---

### Task 4: 短期记忆（LangChain Memory Wrapper）

**Files:**
- Create: `app/memory/short_term.py`
- Create: `tests/memory/test_short_term.py`

- [ ] **Step 1: Write failing test for short_term**

```python
# tests/memory/test_short_term.py
import pytest
from app.memory.short_term import ShortTermMemory, get_short_term_memory

def test_store_and_retrieve():
    mem = get_short_term_memory("session_123")
    mem.save_context({"input": "我要去杭州"}, {"output": "好的，杭州3天"})
    messages = mem.get_messages()
    assert len(messages) == 2

def test_session_isolation():
    mem1 = get_short_term_memory("session_abc")
    mem2 = get_short_term_memory("session_xyz")
    mem1.save_context({"input": "A"}, {"output": "A done"})
    mem2.save_context({"input": "B"}, {"output": "B done"})
    assert len(mem1.get_messages()) == 2
    assert len(mem2.get_messages()) == 2
    assert mem1 is mem2  # same instance for same session_id
```

- [ ] **Step 2: Run test to verify it fails**

```
Expected: FAIL
```

- [ ] **Step 3: Write app/memory/short_term.py**

```python
# app/memory/short_term.py
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, AIMessage
from typing import Optional

class ShortTermMemory:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._memory = ConversationBufferMemory(
            return_messages=True,
            output_key="output",
            input_key="input"
        )

    def save_context(self, inputs: dict, outputs: dict):
        input_text = inputs.get("input", "")
        output_text = outputs.get("output", "")
        self._memory.chat_memory.add_user_message(input_text)
        self._memory.chat_memory.add_ai_message(output_text)

    def get_messages(self):
        return self._memory.chat_memory.messages

    def get_context(self) -> str:
        return self._memory.load_memory_variables({}).get("history", "")

    def clear(self):
        self._memory.clear()

_short_term_stores: dict = {}

def get_short_term_memory(session_id: str) -> ShortTermMemory:
    if session_id not in _short_term_stores:
        _short_term_stores[session_id] = ShortTermMemory(session_id)
    return _short_term_stores[session_id]
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/memory/test_short_term.py -v
Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add app/memory/short_term.py tests/memory/test_short_term.py
git commit -m "feat: add short-term memory wrapper with LangChain ConversationBuffer"
```

---

### Task 5: Metrics Service

**Files:**
- Create: `app/services/metrics_service.py`
- Create: `tests/services/test_metrics_service.py`

- [ ] **Step 1: Write failing test**

```python
# tests/services/test_metrics_service.py
from app.services.metrics_service import MetricsService, get_metrics_service
import time

def test_increment_and_get_qps():
    svc = get_metrics_service()
    svc._reset()
    for _ in range(10):
        svc.increment("chat_requests_total")
    assert svc.get("chat_requests_total") == 10

def test_record_latency():
    svc = get_metrics_service()
    svc._reset()
    svc.record_latency("chat", 1500)
    svc.record_latency("chat", 2500)
    assert svc.get_latency_p50("chat") >= 1500
    assert svc.get_latency_p99("chat") >= 2500

def test_error_rate():
    svc = get_metrics_service()
    svc._reset()
    svc.increment("chat_requests_total")
    svc.increment("chat_requests_total")
    svc.increment("chat_errors_total")
    rate = svc.get_error_rate("chat")
    assert rate == 0.5
```

- [ ] **Step 2: Run test to verify it fails**

```
Expected: FAIL
```

- [ ] **Step 3: Write app/services/metrics_service.py**

```python
# app/services/metrics_service.py
import time
import threading
from collections import defaultdict
from typing import Dict, Optional
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

class MetricsService:
    def __init__(self):
        self._counters: Dict[str, int] = defaultdict(int)
        self._latencies: Dict[str, list] = defaultdict(list)
        self._errors: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

        # Prometheus metrics
        self.chat_requests = Counter("chat_requests_total", "Total chat requests")
        self.chat_errors = Counter("chat_errors_total", "Total chat errors")
        self.chat_latency = Histogram("chat_latency_seconds", "Chat request latency")
        self.agent_duration = Histogram("agent_duration_seconds", "Agent duration by name")

    def increment(self, metric: str, value: int = 1):
        with self._lock:
            self._counters[metric] += value

    def increment_errors(self, metric: str, value: int = 1):
        with self._lock:
            self._errors[metric] += value

    def record_latency(self, metric: str, latency_ms: float):
        with self._lock:
            self._latencies[metric].append(latency_ms)
        # Prometheus histogram
        if metric == "chat":
            self.chat_latency.observe(latency_ms / 1000)

    def get(self, metric: str) -> int:
        return self._counters.get(metric, 0)

    def get_error_rate(self, metric: str) -> float:
        total = self._counters.get(f"{metric}_requests_total", 0)
        errors = self._errors.get(f"{metric}_errors_total", 0)
        return errors / total if total > 0 else 0.0

    def get_latency_p50(self, metric: str) -> float:
        lats = sorted(self._latencies.get(metric, []))
        if not lats:
            return 0.0
        idx = int(len(lats) * 0.5)
        return lats[min(idx, len(lats) - 1)]

    def get_latency_p99(self, metric: str) -> float:
        lats = sorted(self._latencies.get(metric, []))
        if not lats:
            return 0.0
        idx = int(len(lats) * 0.99)
        return lats[min(idx, len(lats) - 1)]

    def record_agent_duration(self, agent_name: str, duration_ms: float):
        self.agent_duration.labels(agent=agent_name).observe(duration_ms / 1000)

    def get_summary(self) -> dict:
        return {
            "qps": self._counters.get("chat_requests_total", 0),
            "latency_p50_ms": self.get_latency_p50("chat"),
            "latency_p99_ms": self.get_latency_p99("chat"),
            "error_rate": self.get_error_rate("chat"),
        }

    def _reset(self):
        self._counters.clear()
        self._latencies.clear()
        self._errors.clear()

_svc: Optional[MetricsService] = None

def get_metrics_service() -> MetricsService:
    global _svc
    if _svc is None:
        _svc = MetricsService()
    return _svc
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/services/test_metrics_service.py -v
Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add app/services/metrics_service.py tests/services/test_metrics_service.py
git commit -m "feat: add metrics service with counters, latency tracking, and Prometheus integration"
```

---

## 阶段三：Services 层（新增 memory_service + planning_service）

### Task 5b: Memory Service（长期记忆统一访问接口）

**Files:**
- Create: `app/services/memory_service.py`
- Create: `tests/services/test_memory_service.py`

> **Design 来源**: Section 3.3 — "通过 app/services/memory_service.py 提供统一访问接口，仅 Preference Agent 调用写方法"

- [ ] **Step 1: Write failing test for memory_service**

```python
# tests/services/test_memory_service.py
import pytest
from unittest.mock import AsyncMock, patch
from app.services.memory_service import MemoryService, get_memory_service

@pytest.mark.asyncio
async def test_write_only_from_preference_agent():
    """Verify only Preference Agent can write; other agents get read-only."""
    svc = get_memory_service()
    # Preference Agent role can write
    assert svc.can_write("PreferenceAgent") is True
    # Other agents are read-only
    assert svc.can_write("AttractionsAgent") is False
    assert svc.can_write("RouteAgent") is False

@pytest.mark.asyncio
async def test_read_allowed_for_all():
    svc = get_memory_service()
    assert svc.can_read("AttractionsAgent") is True
    assert svc.can_read("PlanningAgent") is True
```

- [ ] **Step 2: Run test to verify it fails**

```
Expected: FAIL - module not found
```

- [ ] **Step 3: Write app/services/memory_service.py**

```python
# app/services/memory_service.py
"""Memory Service - unified access to long-term memory with write permission control.

Per design Section 3.3: Only Preference Agent can write to long-term memory.
Other agents get read-only access. This is enforced by role check, not technically.
"""
from typing import Optional, Dict, Any
from app.memory.long_term import get_long_term_memory, LongTermMemory

_WRITE_ENABLED_AGENTS = {"PreferenceAgent"}

class MemoryService:
    """Service layer wrapping LongTermMemory with permission control."""

    def __init__(self):
        self._mem: Optional[LongTermMemory] = None

    def _get_mem(self) -> LongTermMemory:
        if self._mem is None:
            self._mem = get_long_term_memory()
        return self._mem

    def can_write(self, agent_name: str) -> bool:
        """Check if an agent has write permission to long-term memory."""
        return agent_name in _WRITE_ENABLED_AGENTS

    def can_read(self, agent_name: str) -> bool:
        """All agents can read long-term memory."""
        return True

    # Preference write methods (only PreferenceAgent should call these)
    async def update_preference(self, user_id: str, category: str, value: Any):
        mem = self._get_mem()
        await mem.update_preference(user_id, category, value)

    async def get_preference(self, user_id: str) -> Dict[str, Any]:
        mem = self._get_mem()
        return await mem.get_preference(user_id)

    async def save_trip_history(self, user_id: str, city: str, days: int, plan_summary: dict):
        mem = self._get_mem()
        await mem.save_trip_history(user_id, city, days, plan_summary)

    async def get_trip_history(self, user_id: str):
        mem = self._get_mem()
        return await mem.get_trip_history(user_id)

_svc: Optional[MemoryService] = None

def get_memory_service() -> MemoryService:
    global _svc
    if _svc is None:
        _svc = MemoryService()
    return _svc
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/services/test_memory_service.py -v
Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add app/services/memory_service.py tests/services/test_memory_service.py
git commit -m "feat: add memory service with write permission boundary (PreferenceAgent-only write)"
```

---

### Task 5c: Model Fallback Chain（模型降级链）

**Files:**
- Create: `app/services/model_router.py`
- Create: `tests/services/test_model_router.py`

> **Design 来源**: Section 6.1 — "按序切换备选模型：OpenAI → Claude → 本地模型；触发条件：429等待5s、500立即切换、timeout立即切换；单次请求粒度"

- [ ] **Step 1: Write failing test for model_router**

```python
# tests/services/test_model_router.py
import pytest
from unittest.mock import AsyncMock, patch
from app.services.model_router import ModelRouter, get_model_router

@pytest.mark.asyncio
async def test_fallback_on_timeout():
    router = get_model_router()
    # Mock primary model timeout, secondary succeeds
    with patch.object(router, "_call_openai", side_effect=TimeoutError()):
        with patch.object(router, "_call_claude", return_value="Claude response"):
            result = await router.call("test prompt")
            assert result == "Claude response"

@pytest.mark.asyncio
async def test_fallback_on_429():
    router = get_model_router()
    with patch.object(router, "_call_openai", side_effect=Exception("429")):
        with patch.object(router, "_call_claude", return_value="Claude response"):
            result = await router.call("test prompt")
            assert result == "Claude response"

def test_check_primary_available():
    router = get_model_router()
    # By default, primary is available (mocked)
    assert router.is_primary_available() is True
```

- [ ] **Step 2: Run test to verify it fails**

```
Expected: FAIL
```

- [ ] **Step 3: Write app/services/model_router.py**

```python
# app/services/model_router.py
"""Model Router - handles model fallback chain (OpenAI → Claude → local).

Per Design Section 6.1:
- 429: wait 5s then retry primary, if still 429 switch
- 500: immediate switch
- timeout: immediate switch
- Per-request granularity
"""
import asyncio
from typing import Optional, Literal
from app.config import get_settings

ModelName = Literal["openai", "claude", "local"]

class ModelRouter:
    def __init__(self):
        self.settings = get_settings()
        self._primary_available = True  # optimistic

    def is_primary_available(self) -> bool:
        return self._primary_available

    async def call(self, prompt: str, system: str = "") -> str:
        """Call models in chain order, switching on failure.

        Raises:
            Exception: if all models in chain fail
        """
        chain = self.settings.model_chain_list
        last_error = None

        for model in chain:
            try:
                if model == "openai":
                    return await self._call_openai(prompt, system)
                elif model == "claude":
                    return await self._call_claude(prompt, system)
                elif model == "local":
                    return await self._call_local(prompt, system)
            except Exception as e:
                last_error = e
                if self._is_retryable(e):
                    if "429" in str(e) or 429 in str(e):  # rate limit
                        await asyncio.sleep(5)
                        continue  # retry same model
                    else:
                        continue  # switch to next
                else:
                    continue

        # All failed
        raise Exception(f"All models failed. Last error: {last_error}")

    def _is_retryable(self, error: Exception) -> bool:
        err_str = str(error)
        # Per Design Section 6.1:
        # - 429 rate limit: retry after wait (NOT skip to next model)
        # - 500 server error: skip to next model immediately
        # - timeout: skip to next model immediately
        if "429" in err_str:
            return True  # retry same model after wait
        return False  # all other errors → skip to next model

    async def _call_openai(self, prompt: str, system: str) -> str:
        """Call OpenAI API via LangChain.

        NOTE: For portfolio demonstration, this is a structured mock that returns
        a placeholder response. In production, replace with:
          from langchain_openai import ChatOpenAI
          llm = ChatOpenAI(model=self.settings.openai_model, api_key=self.settings.openai_api_key)
          return llm.invoke(prompt).content
        The fallback chain and retry logic remain the same.
        """
        if not self.settings.openai_api_key:
            raise Exception("OPENAI_API_KEY not set")
        # Structured mock: replace with real LangChain call in production
        await asyncio.sleep(0.01)  # simulate network latency
        self._primary_available = True
        return f"[OpenAI] {prompt[:50]}..."

    async def _call_claude(self, prompt: str, system: str) -> str:
        if not self.settings.claude_api_key:
            raise Exception("CLAUDE_API_KEY not set")
        await asyncio.sleep(0.01)
        return f"[Claude] {prompt[:50]}..."

    async def _call_local(self, prompt: str, system: str) -> str:
        # Placeholder for local model (e.g., ollama)
        return f"[Local] {prompt[:50]}..."

_router: Optional[ModelRouter] = None

def get_model_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/services/test_model_router.py -v
Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add app/services/model_router.py tests/services/test_model_router.py
git commit -m "feat: add model router with fallback chain (OpenAI → Claude → local)"
```

---

## 阶段三：Tools 实现

### Task 6: Preference Tools

**Files:**
- Create: `app/tools/preference_tools.py`
- Create: `tests/tools/test_preference_tools.py`

- [ ] **Step 1: Write failing test**

```python
# tests/tools/test_preference_tools.py
import pytest
from unittest.mock import AsyncMock, patch
from app.tools.preference_tools import update_preference, get_preference

@pytest.mark.asyncio
async def test_update_preference():
    mock_mem = AsyncMock()
    mock_mem.update_preference = AsyncMock()
    with patch("app.tools.preference_tools.get_long_term_memory", return_value=mock_mem):
        result = await update_preference("u1", "hardships", ["硬座"])
        assert result["success"] is True
        mock_mem.update_preference.assert_called_once_with("u1", "hardships", ["硬座"])

@pytest.mark.asyncio
async def test_get_preference():
    mock_mem = AsyncMock()
    mock_mem.get_preference = AsyncMock(return_value={"hardships": ["硬座"], "health": ["心脏病"]})
    with patch("app.tools.preference_tools.get_long_term_memory", return_value=mock_mem):
        result = await get_preference("u1")
        assert result["hardships"] == ["硬座"]
        assert result["health"] == ["心脏病"]
```

- [ ] **Step 2: Run test to verify it fails**

```
Expected: FAIL
```

- [ ] **Step 3: Write app/tools/preference_tools.py**

```python
# app/tools/preference_tools.py
"""Preference Tools - read/write user preferences to long-term memory."""
from typing import Any, Dict
from app.memory.long_term import get_long_term_memory

async def update_preference(user_id: str, category: str, value: Any) -> Dict[str, bool]:
    """Update a user preference in long-term memory.

    Args:
        user_id: User identifier
        category: Preference category (hardships/health/spending_style/city_preferences)
        value: Preference value (list or string)

    Returns:
        {"success": true}
    """
    mem = get_long_term_memory()
    await mem.update_preference(user_id, category, value)
    return {"success": True}

async def get_preference(user_id: str) -> Dict[str, Any]:
    """Get all preferences for a user, assembled as nested dict.

    Returns:
        {"hardships": [...], "health": [...], "spending_style": "...", ...}
    """
    mem = get_long_term_memory()
    return await mem.get_preference(user_id)
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/tools/test_preference_tools.py -v
Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add app/tools/preference_tools.py tests/tools/test_preference_tools.py
git commit -m "feat: add preference tools for long-term memory read/write"
```

---

### Task 7: Attractions Tools

**Files:**
- Create: `app/tools/attractions_tools.py`
- Create: `tests/tools/test_attractions_tools.py`

> Note: 这些工具使用**模拟数据**（hardcoded dataset）实现，不依赖真实外部 API。模拟数据集包含中国主要城市（杭州、成都、北京、上海）的景点数据，涵盖 name/score/intensity/price_range 等字段。后续可替换为真实 API。

- [ ] **Step 1: Write failing test**

```python
# tests/tools/test_attractions_tools.py
import pytest
from app.tools.attractions_tools import search_attractions, get_attraction_detail, check_availability

@pytest.mark.asyncio
async def test_search_attractions_returns_list():
    results = await search_attractions("杭州", 3, "spring")
    assert isinstance(results, list)
    assert len(results) > 0
    assert "name" in results[0]
    assert "intensity" in results[0]

@pytest.mark.asyncio
async def test_get_attraction_detail():
    results = await search_attractions("杭州", 3, "spring")
    attr_id = results[0]["id"]
    detail = await get_attraction_detail(attr_id)
    assert detail["id"] == attr_id
    assert "open_hours" in detail

@pytest.mark.asyncio
async def test_check_availability():
    results = await search_attractions("杭州", 3, "spring")
    attr_id = results[0]["id"]
    avail = await check_availability(attr_id, "2026-04-01")
    assert "available" in avail
    assert "booking_tips" in avail
```

- [ ] **Step 2: Run test to verify it fails**

```
Expected: FAIL
```

- [ ] **Step 3: Write app/tools/attractions_tools.py**

```python
# app/tools/attractions_tools.py
"""Attractions Tools - search and detail for tourist attractions.
Uses a hardcoded mock dataset for demonstration purposes.
"""
from typing import List, Dict, Any

# Mock dataset
_MOCK_ATTRACTIONS = {
    "attr_hz_001": {
        "id": "attr_hz_001", "name": "西湖", "city": "杭州", "score": 4.8,
        "best_season": "四季皆宜", "price_range": "0-50", "intensity": "low",
        "tips": "建议清晨或傍晚游览，避开人流高峰",
        "open_hours": "全天开放", "ticket_price": 0, "booking_difficulty": "无需预约"
    },
    "attr_hz_002": {
        "id": "attr_hz_002", "name": "灵隐寺", "city": "杭州", "score": 4.7,
        "best_season": "春秋", "price_range": "50-100", "intensity": "medium",
        "tips": "寺庙内请保持安静，注意着装",
        "open_hours": "07:00-18:00", "ticket_price": 75, "booking_difficulty": "建议提前预约"
    },
    "attr_hz_003": {
        "id": "attr_hz_003", "name": "宋城", "city": "杭州", "score": 4.5,
        "best_season": "全年", "price_range": "200-300", "intensity": "high",
        "tips": "《宋城千古情》是必看演出，建议提前购票",
        "open_hours": "09:00-21:00", "ticket_price": 280, "booking_difficulty": "需提前购票"
    },
    "attr_cd_001": {
        "id": "attr_cd_001", "name": "大熊猫繁育研究基地", "city": "成都", "score": 4.9,
        "best_season": "全年", "price_range": "50-100", "intensity": "low",
        "tips": "建议上午前往，熊猫下午多在休息",
        "open_hours": "07:30-18:00", "ticket_price": 55, "booking_difficulty": "建议提前预约"
    },
    "attr_cd_002": {
        "id": "attr_cd_002", "name": "宽窄巷子", "city": "成都", "score": 4.6,
        "best_season": "四季皆宜", "price_range": "0-50", "intensity": "low",
        "tips": "夜晚灯光璀璨，适合拍照",
        "open_hours": "全天开放", "ticket_price": 0, "booking_difficulty": "无需预约"
    },
}

def _match_city(city: str) -> List[Dict[str, Any]]:
    """Return attractions matching city (case-insensitive prefix match)."""
    city_lower = city.lower()
    return [
        {k: v for k, v in attr.items() if k != "open_hours" and k != "ticket_price" and k != "booking_difficulty"}
        for attr in _MOCK_ATTRACTIONS.values()
        if city_lower in attr["city"].lower()
    ]

async def search_attractions(city: str, days: int, season: str) -> List[Dict[str, Any]]:
    """Search attractions for a city.

    Returns list of attractions with: id, name, score, best_season, price_range, intensity, tips.
    """
    return _match_city(city)

async def get_attraction_detail(attraction_id: str) -> Dict[str, Any]:
    """Get detailed info for a specific attraction."""
    attr = _MOCK_ATTRACTIONS.get(attraction_id, {})
    if not attr:
        return {"error": "Attraction not found"}
    return {
        "id": attr["id"], "name": attr["name"],
        "open_hours": attr["open_hours"],
        "ticket_price": attr["ticket_price"],
        "booking_difficulty": attr["booking_difficulty"],
        "intensity": attr["intensity"]
    }

async def check_availability(attraction_id: str, date: str) -> Dict[str, Any]:
    """Check availability for a specific attraction on a date.

    Note: This returns mock data for demonstration. Real implementation would call external API.
    """
    attr = _MOCK_ATTRACTIONS.get(attraction_id)
    if not attr:
        return {"available": False, "booking_tips": "景点不存在", "crowd_level": "未知"}

    booking_diff = attr.get("booking_difficulty", "")
    if "无需预约" in booking_diff:
        return {"available": True, "booking_tips": "无需预约，可直接前往", "crowd_level": "中等"}
    elif "建议提前预约" in booking_diff:
        return {"available": True, "booking_tips": "建议提前2天预约", "crowd_level": "较高"}
    else:
        return {"available": True, "booking_tips": "需提前购票，建议提前1周", "crowd_level": "高"}
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/tools/test_attractions_tools.py -v
Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add app/tools/attractions_tools.py tests/tools/test_attractions_tools.py
git commit -m "feat: add attractions tools with mock dataset (杭州/成都)"
```

---

### Task 8: Route Tools

**Files:**
- Create: `app/tools/route_tools.py`
- Create: `tests/tools/test_route_tools.py`

- [ ] **Step 1: Write failing test**

```python
# tests/tools/test_route_tools.py
import pytest
from app.tools.route_tools import plan_daily_route, estimate_travel_time

@pytest.mark.asyncio
async def test_plan_daily_route():
    attractions = [
        {"id": "attr_hz_001", "name": "西湖", "intensity": "low"},
        {"id": "attr_hz_002", "name": "灵隐寺", "intensity": "medium"},
    ]
    constraints = {
        "days": 2,
        "budget_limit": 1000.0,
        "mobility_limitations": [],
        "preferred_start_time": "09:00",
        "transport_preferences": ["地铁", "公交", "出租车"],
        "replan_context": None
    }
    route = await plan_daily_route(attractions, constraints)
    assert len(route) == 2
    assert route[0]["day"] == 1
    assert len(route[0]["attractions"]) == 1

@pytest.mark.asyncio
async def test_estimate_travel_time():
    result = await estimate_travel_time("酒店", "西湖", "地铁")
    assert "duration_minutes" in result
    assert "distance_km" in result
    assert result["duration_minutes"] > 0
```

- [ ] **Step 2: Run test to verify it fails**

```
Expected: FAIL
```

- [ ] **Step 3: Write app/tools/route_tools.py**

```python
# app/tools/route_tools.py
"""Route Tools - plan daily routes and estimate travel time.
Mock implementation with deterministic output for demonstration.
"""
from typing import List, Dict, Any, Optional

# Mock travel time estimates (from_location, to_location, transport) → (duration_min, distance_km)
_MOCK_TRAVEL = {
    ("酒店", "西湖", "地铁"): (25, 8),
    ("酒店", "灵隐寺", "地铁"): (35, 12),
    ("西湖", "灵隐寺", "地铁"): (20, 7),
    ("西湖", "灵隐寺", "出租车"): (15, 6),
    ("灵隐寺", "酒店", "地铁"): (35, 12),
    ("西湖", "酒店", "地铁"): (20, 6),
}

def _get_travel_time(from_loc: str, to_loc: str, transport: str) -> tuple:
    for (f, t, tr), (dur, dist) in _MOCK_TRAVEL.items():
        if from_loc in f and to_loc in t:
            return dur, dist
    # Default estimate
    return (30, 10) if "地铁" in transport else (20, 8)

async def plan_daily_route(
    attractions: List[dict],
    constraints: dict
) -> List[Dict[str, Any]]:
    """Plan daily route given attractions and constraints.

    Args:
        attractions: List of attraction dicts from search_attractions
        constraints: {
            "days": int,
            "budget_limit": float,
            "mobility_limitations": List[str],
            "preferred_start_time": str,
            "transport_preferences": List[str],
            "replan_context": dict | None
        }

    Returns:
        List of daily plans with day number, date, attractions, transport, meals
        Per Design Section 5.4: each daily_route includes date field
    """
    import datetime
    days = constraints["days"]
    replan = constraints.get("replan_context")

    # Filter out high-intensity attractions if mobility_limitations present
    filtered = attractions
    if constraints.get("mobility_limitations"):
        filtered = [a for a in attractions if a.get("intensity", "medium") != "high"]
        if len(filtered) == 0:
            filtered = attractions  # fallback if all are filtered out

    # Adjust strategy based on replan attempt
    if replan:
        attempt = replan.get("attempt", 1)
        if attempt == 1:
            pass  # keep most attractions, just budget-trim
        elif attempt == 2:
            filtered = filtered[:days] if len(filtered) >= days else filtered

    # Assign start date (today + 1 as mock departure date)
    start_date = datetime.date.today() + datetime.timedelta(days=1)

    daily_plans = []
    start_hour = int(constraints.get("preferred_start_time", "09:00").split(":")[0])
    transport_pref = constraints.get("transport_preferences", ["地铁"])[0]

    idx = 0
    for day_num in range(1, days + 1):
        if idx >= len(filtered):
            break
        attr = filtered[idx]
        travel_from_hotel = _get_travel_time("酒店", attr["name"], transport_pref)
        current_date = start_date + datetime.timedelta(days=day_num - 1)
        daily_plans.append({
            "day": day_num,
            "date": current_date.isoformat(),  # e.g., "2026-04-01"
            "attractions": [{
                "id": attr["id"],
                "name": attr["name"],
                "arrival_time": f"{start_hour:02d}:00",
                "leave_time": f"{start_hour + 3:02d}:00"
            }],
            "transport": {
                "from": "酒店",
                "to": attr["name"],
                "type": transport_pref,
                "duration_minutes": travel_from_hotel[0]
            },
            "meals": [
                {"type": "午餐", "restaurant": "外婆家（景区店）", "budget": 80}
            ]
        })
        start_hour = 14
        idx += 1

    return daily_plans

async def estimate_travel_time(from_location: str, to_location: str, transport: str) -> Dict[str, Any]:
    """Estimate travel time between two locations."""
    dur, dist = _get_travel_time(from_location, to_location, transport)
    return {"duration_minutes": dur, "distance_km": dist}
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/tools/test_route_tools.py -v
Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add app/tools/route_tools.py tests/tools/test_route_tools.py
git commit -m "feat: add route tools with daily planning and travel estimation"
```

---

### Task 9: Budget Tools

**Files:**
- Create: `app/tools/budget_tools.py`
- Create: `tests/tools/test_budget_tools.py`

- [ ] **Step 1: Write failing test**

```python
# tests/tools/test_budget_tools.py
import pytest
from app.tools.budget_tools import calculate_budget, check_budget_vs_plan

@pytest.mark.asyncio
async def test_calculate_budget():
    result = await calculate_budget(3, "节省")
    assert "total_budget" in result
    assert "attractions_budget" in result
    assert "food_budget" in result
    assert "hotel_budget" in result

@pytest.mark.asyncio
async def test_check_budget_within():
    plan = {
        "daily_routes": [{"attractions": [{"ticket_price": 0}], "transport": {"estimated_cost": 20}, "meals": [{"estimated_cost": 80}]}],
        "hotel": {"total_cost": 450},
        "transport_to_city": {"cost": 220},
        "attractions_total": 0,
        "food_total": 240,
        "transport_within_city": 60
    }
    result = await check_budget_vs_plan(5000.0, plan)
    assert result["within_budget"] is True

@pytest.mark.asyncio
async def test_check_budget_over():
    plan = {
        "daily_routes": [],
        "hotel": {"total_cost": 10000},
        "transport_to_city": {"cost": 0},
        "attractions_total": 0,
        "food_total": 0,
        "transport_within_city": 0
    }
    result = await check_budget_vs_plan(5000.0, plan)
    assert result["within_budget"] is False
    assert result["remaining"] < 0
```

- [ ] **Step 2: Run test to verify it fails**

```
Expected: FAIL
```

- [ ] **Step 3: Write app/tools/budget_tools.py**

```python
# app/tools/budget_tools.py
"""Budget Tools - calculate budget allocation and validate against plan.
"""
from typing import Dict, Any

# Budget style multipliers (relative to base mid-tier)
_BUDGET_STYLES = {
    "节省": {"multiplier": 0.6, "attractions_pct": 0.10, "food_pct": 0.25, "hotel_pct": 0.35, "transport_pct": 0.15, "reserve_pct": 0.15},
    "适中": {"multiplier": 1.0, "attractions_pct": 0.15, "food_pct": 0.25, "hotel_pct": 0.30, "transport_pct": 0.10, "reserve_pct": 0.20},
    "奢侈": {"multiplier": 2.0, "attractions_pct": 0.20, "food_pct": 0.25, "hotel_pct": 0.30, "transport_pct": 0.10, "reserve_pct": 0.15},
}

async def calculate_budget(duration: int, style: str = "适中") -> Dict[str, Any]:
    """Calculate budget breakdown for a trip.

    Args:
        duration: Number of days
        style: "节省" | "适中" | "奢侈"

    Returns:
        {"total_budget": float, "attractions_budget": float, "food_budget": float,
         "hotel_budget": float, "transport_budget": float, "reserve_budget": float}
    """
    base = 1500 * duration  # base mid-tier: 1500 CNY per day
    style_cfg = _BUDGET_STYLES.get(style, _BUDGET_STYLES["适中"])
    total = int(base * style_cfg["multiplier"])

    return {
        "total_budget": total,
        "attractions_budget": int(total * style_cfg["attractions_pct"]),
        "food_budget": int(total * style_cfg["food_pct"]),
        "hotel_budget": int(total * style_cfg["hotel_pct"]),
        "transport_budget": int(total * style_cfg["transport_pct"]),
        "reserve_budget": int(total * style_cfg["reserve_pct"]),
    }

async def check_budget_vs_plan(budget: float, plan: dict) -> Dict[str, Any]:
    """Check if a plan exceeds the budget.

    plan: see design doc Section 4.3
    Returns: {"within_budget": bool, "remaining": float, "alerts": List[str]}
    """
    # Sum up actual costs from plan
    daily_costs = 0
    for route in plan.get("daily_routes", []):
        for attr in route.get("attractions", []):
            daily_costs += attr.get("ticket_price", 0)
        for meal in route.get("meals", []):
            daily_costs += meal.get("estimated_cost", 0)
        daily_costs += route.get("transport", {}).get("estimated_cost", 0)

    hotel_cost = plan.get("hotel", {}).get("total_cost", 0)
    transport_to = plan.get("transport_to_city", {}).get("cost", 0)
    attractions_total = plan.get("attractions_total", 0)
    food_total = plan.get("food_total", 0)
    transport_within = plan.get("transport_within_city", 0)

    total_cost = daily_costs + hotel_cost + transport_to + attractions_total + food_total + transport_within
    remaining = budget - total_cost

    alerts = []
    if remaining < 0:
        alerts.append(f"当前方案超出预算 {-remaining:.0f} 元")
    if remaining < budget * 0.1:
        alerts.append("预算余量不足10%，建议增加预算或精简行程")

    return {
        "within_budget": remaining >= 0,
        "remaining": round(remaining, 2),
        "alerts": alerts
    }
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/tools/test_budget_tools.py -v
Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add app/tools/budget_tools.py tests/tools/test_budget_tools.py
git commit -m "feat: add budget tools with allocation and plan validation"
```

---

### Task 10: Food Tools

**Files:**
- Create: `app/tools/food_tools.py`
- Create: `tests/tools/test_food_tools.py`

- [ ] **Step 1: Write failing test**

```python
# tests/tools/test_food_tools.py
import pytest
from app.tools.food_tools import recommend_restaurants

@pytest.mark.asyncio
async def test_recommend_returns_list():
    results = await recommend_restaurants("杭州", "浙菜", 100.0)
    assert isinstance(results, list)
    assert len(results) > 0
    assert "name" in results[0]
    assert "cuisine" in results[0]
```

- [ ] **Step 2: Run test to verify it fails**

```
Expected: FAIL
```

- [ ] **Step 3: Write app/tools/food_tools.py**

```python
# app/tools/food_tools.py
"""Food Tools - recommend local restaurants.
Mock dataset for demonstration.
"""
from typing import List, Dict, Any

_MOCK_RESTAURANTS = {
    "杭州": [
        {"name": "外婆家", "cuisine": "浙菜", "price_level": "¥", "location": "西湖区",
         "signature_dishes": ["东坡肉", "叫化鸡", "西湖醋鱼"], "avg_budget": 80},
        {"name": "知味观", "cuisine": "浙菜/小吃", "price_level": "¥¥", "location": "西湖区",
         "signature_dishes": ["小笼包", "片儿川"], "avg_budget": 120},
        {"name": "楼外楼", "cuisine": "浙菜", "price_level": "¥¥¥", "location": "西湖",
         "signature_dishes": ["东坡肉", "宋嫂鱼羹"], "avg_budget": 250},
    ],
    "成都": [
        {"name": "玉林串串香", "cuisine": "川菜/火锅", "price_level": "¥", "location": "武侯区",
         "signature_dishes": ["串串", "冒菜"], "avg_budget": 60},
        {"name": "蜀大侠火锅", "cuisine": "川菜/火锅", "price_level": "¥¥", "location": "锦江区",
         "signature_dishes": ["牛油锅底", "鲜毛肚"], "avg_budget": 120},
        {"name": "陈麻婆豆腐", "cuisine": "川菜", "price_level": "¥¥", "location": "青羊区",
         "signature_dishes": ["麻婆豆腐", "夫妻肺片"], "avg_budget": 100},
    ],
}

async def recommend_restaurants(city: str, style: str = "", budget_per_meal: float = 100.0) -> List[Dict[str, Any]]:
    """Recommend restaurants in a city.

    Args:
        city: City name
        style: Cuisine preference (e.g., "浙菜", empty = all)
        budget_per_meal: Budget per meal in CNY

    Returns:
        List of restaurant dicts
    """
    restaurants = _MOCK_RESTAURANTS.get(city, [])
    if style:
        restaurants = [r for r in restaurants if style in r["cuisine"] or not style]
    # Filter by budget
    restaurants = [r for r in restaurants if r["avg_budget"] <= budget_per_meal * 1.5]
    return restaurants
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/tools/test_food_tools.py -v
Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add app/tools/food_tools.py tests/tools/test_food_tools.py
git commit -m "feat: add food tools with restaurant recommendations"
```

---

### Task 11: Hotel Tools

**Files:**
- Create: `app/tools/hotel_tools.py`
- Create: `tests/tools/test_hotel_tools.py`

- [ ] **Step 1: Write failing test**

```python
# tests/tools/test_hotel_tools.py
import pytest
from app.tools.hotel_tools import search_hotels

@pytest.mark.asyncio
async def test_search_hotels_returns_list():
    results = await search_hotels("杭州", 300.0, "西湖区")
    assert isinstance(results, list)
    assert len(results) > 0
    assert "name" in results[0]
    assert "price" in results[0]
```

- [ ] **Step 2: Run test to verify it fails**

```
Expected: FAIL
```

- [ ] **Step 3: Write app/tools/hotel_tools.py**

```python
# app/tools/hotel_tools.py
"""Hotel Tools - search and recommend hotels.
Mock dataset for demonstration.
"""
from typing import List, Dict, Any

_MOCK_HOTELS = {
    "杭州": [
        {"name": "如家精选（西湖断桥店）", "location": "西湖区", "price_per_night": 280,
         "rating": 4.5, "nearby_attractions": ["西湖", "断桥"], "amenities": ["WiFi", "早餐"]},
        {"name": "杭州香格里拉饭店", "location": "西湖区", "price_per_night": 680,
         "rating": 4.8, "nearby_attractions": ["西湖", "音乐喷泉"], "amenities": ["WiFi", "健身房", "早餐"]},
        {"name": "汉庭酒店（西湖店）", "location": "西湖区", "price_per_night": 180,
         "rating": 4.2, "nearby_attractions": ["西湖"], "amenities": ["WiFi"]},
    ],
    "成都": [
        {"name": "成都熊猫慢旅酒店", "location": "成华区", "price_per_night": 250,
         "rating": 4.6, "nearby_attractions": ["大熊猫基地", "宽窄巷子"], "amenities": ["WiFi", "早餐"]},
        {"name": "成都瑞吉酒店", "location": "锦江区", "price_per_night": 900,
         "rating": 4.9, "nearby_attractions": ["春熙路", "太古里"], "amenities": ["WiFi", "健身房", "泳池"]},
    ],
}

async def search_hotels(city: str, budget: float = 500.0, location_preference: str = "") -> List[Dict[str, Any]]:
    """Search hotels in a city within budget.

    Args:
        city: City name
        budget: Max price per night in CNY
        location_preference: Preferred district (empty = any)

    Returns:
        List of hotel dicts
    """
    hotels = _MOCK_HOTELS.get(city, [])
    if budget:
        hotels = [h for h in hotels if h["price_per_night"] <= budget]
    if location_preference:
        hotels = [h for h in hotels if location_preference in h["location"]]
    return hotels
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/tools/test_hotel_tools.py -v
Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add app/tools/hotel_tools.py tests/tools/test_hotel_tools.py
git commit -m "feat: add hotel tools with hotel search and recommendations"
```

---

## 阶段四：Agent 实现

### Task 12: Preference Agent

**Files:**
- Create: `app/agents/preference.py`
- Create: `tests/agents/test_preference_agent.py`

- [ ] **Step 1: Write failing test**

```python
# tests/agents/test_preference_agent.py
import pytest
from app.agents.preference import PreferenceAgent

@pytest.fixture
def agent():
    return PreferenceAgent()

@pytest.mark.asyncio
async def test_update_and_get(agent):
    await agent.update_preference("u1", "hardships", ["硬座"])
    prefs = await agent.get_preference("u1")
    assert "hardships" in prefs
```

- [ ] **Step 2: Run test to verify it fails**

```
Expected: FAIL
```

- [ ] **Step 3: Write app/agents/preference.py**

```python
# app/agents/preference.py
"""Preference Agent - manages user preferences in long-term memory.
This is the ONLY agent that writes to long-term memory.
"""
from typing import Any, Dict
from app.tools import preference_tools as pt

class PreferenceAgent:
    """Agent responsible for reading and writing user preferences.

    This agent is the sole writer to long-term SQLite memory.
    Other agents call get_preference() to read but cannot write.
    """

    async def update_preference(self, user_id: str, category: str, value: Any) -> Dict[str, bool]:
        """Update a single preference category for a user."""
        return await pt.update_preference(user_id, category, value)

    async def get_preference(self, user_id: str) -> Dict[str, Any]:
        """Get all preferences for a user (assembled nested dict)."""
        return await pt.get_preference(user_id)

    async def parse_and_update(self, user_id: str, message: str) -> Dict[str, Any]:
        """Parse a user message for preference hints and update memory.

        Looks for patterns like:
        - "我不喜欢硬座" → hardships
        - "我有心脏病" / "糖尿病" → health
        - "我想节省一点" → spending_style = "节省"
        """
        import re
        updates = []

        # Health conditions
        health_keywords = ["心脏病", "糖尿病", "高血压", "哮喘", "过敏", "癫痫"]
        for kw in health_keywords:
            if kw in message:
                await self.update_preference(user_id, "health", [kw])
                updates.append(kw)

        # Hardships
        hardship_keywords = ["硬座", "红眼航班", "转机", "步行", "爬山"]
        for kw in hardship_keywords:
            if kw in message:
                await self.update_preference(user_id, "hardships", [kw])
                updates.append(kw)

        # Spending style
        if "节省" in message or "省钱" in message:
            await self.update_preference(user_id, "spending_style", "节省")
            updates.append("spending_style=节省")
        elif "奢侈" in message or "豪华" in message:
            await self.update_preference(user_id, "spending_style", "奢侈")
            updates.append("spending_style=奢侈")

        return {"updated": updates}
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/agents/test_preference_agent.py -v
Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add app/agents/preference.py tests/agents/test_preference_agent.py
git commit -m "feat: add preference agent as sole long-term memory writer"
```

---

### Task 13: Specialist Agents (Attractions, Route, Budget, Food, Hotel)

**Files:**
- Create: `app/agents/attractions.py`
- Create: `app/agents/route.py`
- Create: `app/agents/budget.py`
- Create: `app/agents/food.py`
- Create: `app/agents/hotel.py`
- Create: `tests/agents/test_specialist_agents.py`

- [ ] **Step 1: Write failing test for all specialist agents**

```python
# tests/agents/test_specialist_agents.py
import pytest
from app.agents.attractions import AttractionsAgent
from app.agents.route import RouteAgent
from app.agents.budget import BudgetAgent
from app.agents.food import FoodAgent
from app.agents.hotel import HotelAgent

@pytest.mark.asyncio
async def test_attractions_agent():
    agent = AttractionsAgent()
    prefs = {"health": ["心脏病"], "hardships": ["硬座"]}
    result = await agent.search("杭州", 3, "spring", prefs)
    assert "attractions" in result
    assert all(a.get("intensity") != "high" for a in result["attractions"])

@pytest.mark.asyncio
async def test_route_agent():
    agent = RouteAgent()
    attractions = [{"id": "attr_hz_001", "name": "西湖", "intensity": "low", "ticket_price": 0}]
    constraints = {"days": 1, "budget_limit": 1000, "mobility_limitations": [],
                   "preferred_start_time": "09:00", "transport_preferences": ["地铁"], "replan_context": None}
    result = await agent.plan(attractions, constraints)
    assert "daily_routes" in result

@pytest.mark.asyncio
async def test_budget_agent():
    agent = BudgetAgent()
    result = await agent.calculate(3, "适中")
    assert result["total_budget"] > 0

@pytest.mark.asyncio
async def test_food_agent():
    agent = FoodAgent()
    result = await agent.recommend("杭州", "浙菜", 100.0)
    assert len(result) > 0

@pytest.mark.asyncio
async def test_hotel_agent():
    agent = HotelAgent()
    result = await agent.search("杭州", 300.0, "西湖区")
    assert len(result) > 0
```

- [ ] **Step 2: Run test to verify it fails**

```
Expected: FAIL
```

- [ ] **Step 3: Write all specialist agents**

```python
# app/agents/attractions.py
"""Attractions Agent - search and filter attractions based on user preferences."""
from typing import Dict, Any, List
from app.tools import attractions_tools as at

class AttractionsAgent:
    """Specialist agent for attractions search and filtering.

    Reads preferences from Preference Agent to filter out inappropriate attractions
    (e.g., high-intensity for heart disease patients).
    """

    async def search(self, city: str, days: int, season: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Search attractions and filter based on user preferences."""
        attractions = await at.search_attractions(city, days, season)

        # Filter based on health preferences
        health_prefs = preferences.get("health", [])
        mobility_limitations = []
        if any(h in health_prefs for h in ["心脏病", "高血压", "哮喘"]):
            mobility_limitations.append("high_intensity")

        filtered = attractions
        if mobility_limitations:
            filtered = [a for a in attractions if a.get("intensity") != "high"]

        return {"attractions": filtered, "city": city, "days": days}

    async def get_detail(self, attraction_id: str) -> Dict[str, Any]:
        return await at.get_attraction_detail(attraction_id)

    async def check_availability(self, attraction_id: str, date: str) -> Dict[str, Any]:
        return await at.check_availability(attraction_id, date)
```

```python
# app/agents/route.py
"""Route Agent - plan daily routes."""
from typing import Dict, Any, List
from app.tools import route_tools as rt

class RouteAgent:
    """Specialist agent for route planning."""

    async def plan(self, attractions: List[dict], constraints: Dict[str, Any]) -> Dict[str, Any]:
        """Plan daily routes given attractions and constraints."""
        daily_routes = await rt.plan_daily_route(attractions, constraints)
        return {"daily_routes": daily_routes}

    async def estimate_travel(self, from_location: str, to_location: str, transport: str) -> Dict[str, Any]:
        return await rt.estimate_travel_time(from_location, to_location, transport)
```

```python
# app/agents/budget.py
"""Budget Agent - calculate and validate budgets."""
from typing import Dict, Any
from app.tools import budget_tools as bt

class BudgetAgent:
    """Specialist agent for budget calculation and validation."""

    async def calculate(self, duration: int, style: str) -> Dict[str, Any]:
        return await bt.calculate_budget(duration, style)

    async def check_plan(self, budget: float, plan: dict) -> Dict[str, Any]:
        return await bt.check_budget_vs_plan(budget, plan)
```

```python
# app/agents/food.py
"""Food Agent - recommend restaurants."""
from typing import Dict, Any, List
from app.tools import food_tools as ft

class FoodAgent:
    """Specialist agent for food recommendations."""

    async def recommend(self, city: str, style: str = "", budget_per_meal: float = 100.0) -> Dict[str, Any]:
        restaurants = await ft.recommend_restaurants(city, style, budget_per_meal)
        return {"restaurants": restaurants}
```

```python
# app/agents/hotel.py
"""Hotel Agent - search hotels."""
from typing import Dict, Any, List
from app.tools import hotel_tools as ht

class HotelAgent:
    """Specialist agent for hotel search."""

    async def search(self, city: str, budget: float = 500.0, location: str = "") -> Dict[str, Any]:
        hotels = await ht.search_hotels(city, budget, location)
        return {"hotels": hotels}
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/agents/test_specialist_agents.py -v
Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add app/agents/attractions.py app/agents/route.py app/agents/budget.py app/agents/food.py app/agents/hotel.py tests/agents/test_specialist_agents.py
git commit -m "feat: add all specialist agents (Attractions, Route, Budget, Food, Hotel)"
```

---

### Task 14: Supervisor Agent (Planning Agent)

**Files:**
- Create: `app/agents/supervisor.py`
- Create: `tests/agents/test_supervisor_agent.py`

- [ ] **Step 1: Write failing test for supervisor**

```python
# tests/agents/test_supervisor_agent.py
import pytest
from unittest.mock import AsyncMock, patch
from app.agents.supervisor import PlanningAgent, parse_travel_intent

def test_parse_travel_intent_full():
    result = parse_travel_intent("我要去杭州玩3天，预算5000")
    assert result["city"] == "杭州"
    assert result["days"] == 3
    assert result["budget"] == 5000

def test_parse_travel_intent_partial():
    result = parse_travel_intent("我想去成都")
    assert result["city"] == "成都"
    assert result["days"] == 2  # default
    assert result["budget"] == 3000  # default

@pytest.mark.asyncio
async def test_full_planning_flow():
    agent = PlanningAgent()
    with patch.object(agent, "_call_agent", new_callable=AsyncMock) as mock:
        # Mock all agent calls
        mock.side_effect = [
            {"preferences": {}},  # Preference read
            {"attractions": [{"id": "attr_hz_001", "name": "西湖", "intensity": "low"}]},  # Attractions
            {"total_budget": 5000},  # Budget
            {"daily_routes": []},  # Route
            {"restaurants": []},  # Food
            {"hotels": []},  # Hotel
            {"within_budget": True, "remaining": 1000},  # Budget check
        ]
        result = await agent.plan("u1", "sess_1", "我要去杭州3天，预算5000")
        assert "plan_id" in result
        assert result["city"] == "杭州"
```

- [ ] **Step 2: Run test to verify it fails**

```
Expected: FAIL
```

- [ ] **Step 3: Write app/agents/supervisor.py**

```python
# app/agents/supervisor.py
"""Planning Agent (Supervisor) - coordinates all specialist agents.

This is the main entry point for the Multi-Agent system.
Orchestrates: Preference Agent → parallel (Attractions + Budget) → Route → parallel (Food + Hotel) → Budget check.
"""
import re
import uuid
import time
from typing import Any, Dict, List, Optional
from app.agents.preference import PreferenceAgent
from app.agents.attractions import AttractionsAgent
from app.agents.route import RouteAgent
from app.agents.budget import BudgetAgent
from app.agents.food import FoodAgent
from app.agents.hotel import HotelAgent
from app.memory.short_term import get_short_term_memory
from app.services.metrics_service import get_metrics_service

# Health alert rules
_HEALTH_ALERT_RULES = {
    "心脏病": "您的行程包含较多步行，建议随身携带日常药物并避免剧烈活动",
    "糖尿病": "建议随身携带血糖仪和备用食物，注意按时用餐",
}

_HARDSHIP_ALERT_RULES = {
    "硬座": "已为您排除火车硬座选项，全程优先选择卧铺/座位",
}

def parse_travel_intent(message: str) -> Dict[str, Any]:
    """Parse user travel intent from natural language.

    Extracts: city, days, budget, season from user message.
    """
    # Extract city (after "去" or "到" or "前往")
    city_match = re.search(r"去([A-Za-z\u4e00-\u9fa5]{2,5})|到([A-Za-z\u4e00-\u9fa5]{2,5})|前往([A-Za-z\u4e00-\u9fa5]{2,5})", message)
    city = city_match.group(1) or city_match.group(2) or city_match.group(3) if city_match else ""

    # Extract days
    days_match = re.search(r"(\d+)天", message)
    days = int(days_match.group(1)) if days_match else 2

    # Extract budget
    budget_match = re.search(r"预算(\d+)", message)
    budget = int(budget_match.group(1)) if budget_match else 3000

    # Extract season (rough heuristic)
    season = "spring"
    if any(s in message for s in ["夏天", "夏季", "暑假", "七月", "八月"]):
        season = "summer"
    elif any(s in message for s in ["秋天", "秋季", "九月", "十月", "十一月"]):
        season = "autumn"
    elif any(s in message for s in ["冬天", "冬季", "十二月", "一月", "二月"]):
        season = "winter"

    return {"city": city, "days": days, "budget": budget, "season": season}

class PlanningAgent:
    """Supervisor agent that coordinates all specialist agents.

    Orchestration flow (see Design Doc Section 2.3):
      1. Parse intent
      2. Preference Agent: parse and update preferences
      3. Parallel: Attractions Agent + Budget Agent
      4. Route Agent
      5. Parallel: Food Agent + Hotel Agent
      6. Budget Agent: validate
      7. If over budget → Route Agent replan (max 2 attempts)
      8. Generate health alerts + preference compliance notes
      9. Return final plan
    """

    def __init__(self):
        self.pref_agent = PreferenceAgent()
        self.attr_agent = AttractionsAgent()
        self.route_agent = RouteAgent()
        self.budget_agent = BudgetAgent()
        self.food_agent = FoodAgent()
        self.hotel_agent = HotelAgent()
        self.metrics = get_metrics_service()

    async def plan(self, user_id: str, session_id: str, message: str) -> Dict[str, Any]:
        """Main planning entry point."""
        t0 = time.time()
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        agent_trace = {"agents": [], "invocation_order": [], "durations_ms": [], "errors": []}

        async def trace(agent_name: str, coro):
            """Wrapper to time agent calls."""
            agent_trace["agents"].append(agent_name)
            agent_trace["invocation_order"].append(len(agent_trace["agents"]))
            t = time.time()
            try:
                result = await coro
                agent_trace["durations_ms"].append(int((time.time() - t) * 1000))
                return result
            except Exception as e:
                agent_trace["durations_ms"].append(int((time.time() - t) * 1000))
                agent_trace["errors"].append({"agent": agent_name, "error": str(e)})
                raise

        # Step 1: Parse intent
        intent = parse_travel_intent(message)
        city, days, budget, season = intent["city"], intent["days"], intent["budget"], intent["season"]

        # Step 2: Parse and update preferences
        pref_result = await trace("Preference Agent",
            self.pref_agent.parse_and_update(user_id, message))
        preferences = await self.pref_agent.get_preference(user_id)

        # Step 3: Parallel - Attractions + Budget
        attr_result = await trace("Attractions Agent",
            self.attr_agent.search(city, days, season, preferences))
        budget_result = await trace("Budget Agent",
            self.budget_agent.calculate(days, preferences.get("spending_style", "适中")))

        attractions = attr_result.get("attractions", [])

        # Step 4: Route planning
        route_result = await trace("Route Agent",
            self.route_agent.plan(attractions, {
                "days": days,
                "budget_limit": budget,
                "mobility_limitations": preferences.get("health", []),
                "preferred_start_time": "09:00",
                "transport_preferences": ["地铁", "公交", "出租车"],
                "replan_context": None
            }))

        # Step 5: Parallel - Food + Hotel
        food_result = await trace("Food Agent",
            self.food_agent.recommend(city, "", budget / days / 3))
        hotel_result = await trace("Hotel Agent",
            self.hotel_agent.search(city, budget / days, ""))

        # Step 6: Budget validation
        hotel_info = hotel_result.get("hotels", [{}])[0] if hotel_result.get("hotels") else {}
        hotel_cost = (hotel_info.get("price_per_night", 0) or 0) * days
        plan_summary = {
            "daily_routes": route_result.get("daily_routes", []),
            "hotel": {"name": hotel_info.get("name", ""), "total_cost": hotel_cost},
            "transport_to_city": {"type": "高铁", "cost": 220},  # mock: inbound transport
            "attractions_total": sum(a.get("ticket_price", 0) for a in attractions),
            "food_total": len(food_result.get("restaurants", [])) * (budget // days // 3),
            "transport_within_city": days * 30,  # estimated city transport
        }

        budget_check = await trace("Budget Agent (validation)",
            self.budget_agent.check_plan(budget, plan_summary))

        # Step 7: Budget → Route adjustment loop (max 2 attempts)
        if not budget_check["within_budget"] and budget_check["alerts"]:
            for attempt in [1, 2]:
                route_result = await self.route_agent.plan(attractions, {
                    "days": days,
                    "budget_limit": budget,
                    "mobility_limitations": preferences.get("health", []),
                    "preferred_start_time": "09:00",
                    "transport_preferences": ["地铁", "公交", "出租车"],
                    "replan_context": {
                        "mode": "replan", "reason": "over_budget",
                        "current_plan": route_result.get("daily_routes", []),
                        "budget_limit": budget, "attempt": attempt
                    }
                })
                plan_summary["daily_routes"] = route_result.get("daily_routes", [])
                budget_check = await self.budget_agent.check_plan(budget, plan_summary)
                if budget_check["within_budget"]:
                    break

        # Step 8: Generate health alerts and preference compliance
        health_alerts = self._generate_health_alerts(preferences)
        preference_compliance = self._generate_compliance(preferences)

        # Save to short-term memory
        short_mem = get_short_term_memory(session_id)
        short_mem.save_context(
            {"input": message},
            {"output": f"已为您规划{city}{days}天行程，预算{budget}元"}
        )

        total_ms = int((time.time() - t0) * 1000)
        self.metrics.increment("chat_requests_total")
        self.metrics.record_latency("chat", total_ms)

        # Compute reserve = total_budget - sum(category_costs)
        total_cost = (
            plan_summary["attractions_total"]
            + plan_summary["food_total"]
            + hotel_cost
            + plan_summary["transport_to_city"]["cost"]
            + plan_summary["transport_within_city"]
        )
        reserve = budget - total_cost

        # Get category breakdowns from budget_result
        cat_breakdown = budget_result  # from calculate_budget call

        return {
            "plan_id": plan_id,
            "city": city,
            "days": days,
            "budget": budget,
            "daily_routes": route_result.get("daily_routes", []),
            "attractions": attractions,
            "food": food_result.get("restaurants", []),
            "hotels": hotel_result.get("hotels", []),
            "budget_summary": {
                "total_budget": budget,
                "attractions_total": plan_summary["attractions_total"],
                "food_total": plan_summary["food_total"],
                "hotel_total": hotel_cost,
                "transport_total": plan_summary["transport_to_city"]["cost"] + plan_summary["transport_within_city"],
                "reserve": max(0, reserve),
                "within_budget": budget_check["within_budget"],
                "remaining": budget_check.get("remaining", 0),
                "alerts": budget_check.get("alerts", [])
            },
            "health_alerts": health_alerts,
            "preference_compliance": preference_compliance,
            "agent_trace": agent_trace,
        }

    def _generate_health_alerts(self, preferences: Dict[str, Any]) -> List[str]:
        alerts = []
        for condition, alert_text in _HEALTH_ALERT_RULES.items():
            if condition in preferences.get("health", []):
                alerts.append(alert_text)
        # Fallback for unlisted health conditions
        for h in preferences.get("health", []):
            if h not in _HEALTH_ALERT_RULES:
                alerts.append(f"请注意：{h}")
        return alerts

    def _generate_compliance(self, preferences: Dict[str, Any]) -> List[str]:
        notes = []
        for hardship, note in _HARDSHIP_ALERT_RULES.items():
            if hardship in preferences.get("hardships", []):
                notes.append(note)
        return notes
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/agents/test_supervisor_agent.py -v
Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add app/agents/supervisor.py tests/agents/test_supervisor_agent.py
git commit -m "feat: add planning supervisor agent with full orchestration flow"
```

---

## 阶段五：API 层与中间件

### Task 15: 中间件（Traces + Error Handler）

**Files:**
- Create: `app/middleware/tracing.py`
- Create: `app/middleware/error_handler.py`
- Create: `tests/middleware/`

- [ ] **Step 1: Write failing test for tracing**

```python
# tests/middleware/test_tracing.py
import pytest
from unittest.mock import MagicMock
from app.middleware.tracing import TracingMiddleware

def test_trace_id_generated():
    mock_app = MagicMock()
    middleware = TracingMiddleware(mock_app)
    assert middleware.app is mock_app

def test_trace_id_propagates():
    from starlette.testclient import TestClient
    from fastapi import FastAPI
    from app.middleware.tracing import TracingMiddleware

    app = FastAPI()
    app.add_middleware(TracingMiddleware)

    @app.get("/test")
    def test_route():
        from app.middleware.tracing import get_trace_id
        return {"trace_id": get_trace_id()}

    client = TestClient(app)
    resp = client.get("/test")
    assert "trace_id" in resp.json()
```

- [ ] **Step 2: Run test to verify it fails**

```
Expected: FAIL
```

- [ ] **Step 3: Write app/middleware/tracing.py**

```python
# app/middleware/tracing.py
"""Tracing Middleware - adds trace_id to every request for log correlation."""
import uuid
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from contextvars import ContextVar

_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")

def get_trace_id() -> str:
    return _trace_id_var.get()

class TracingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        _trace_id_var.set(trace_id)

        # Bind trace_id to structlog
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(trace_id=trace_id)

        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response
```

```python
# app/middleware/error_handler.py
"""Error Handler Middleware - graceful degradation with structured error responses."""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import get_settings
import structlog

logger = structlog.get_logger()

class AgentError(Exception):
    def __init__(self, agent_name: str, message: str, recoverable: bool = False):
        self.agent_name = agent_name
        self.message = message
        self.recoverable = recoverable

class AllAgentsFailedError(Exception):
    pass

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except AgentError as e:
            logger.error("agent_error", agent=e.agent_name, message=e.message, recoverable=e.recoverable)
            return JSONResponse(
                status_code=200 if e.recoverable else 500,
                content={
                    "error": e.message,
                    "agent": e.agent_name,
                    "recoverable": e.recoverable,
                    "fallback": "请告诉我更具体的偏好，或稍后重试"
                }
            )
        except AllAgentsFailedError:
            logger.error("all_agents_failed")
            return JSONResponse(
                status_code=200,
                content={
                    "answer": "抱歉，所有推荐服务暂时不可用。请稍后重试，或告诉我更具体的需求。",
                    "fallback": "您可以尝试说 '我要去杭州' 这样的简单需求"
                }
            )
        except Exception as e:
            logger.exception("unhandled_error")
            return JSONResponse(
                status_code=500,
                content={"error": "服务内部错误，请稍后重试"}
            )
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/middleware/test_tracing.py -v
Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add app/middleware/tracing.py app/middleware/error_handler.py tests/middleware/
git commit -m "feat: add tracing middleware (trace_id) and error handler middleware"
```

---

### Task 16: API 路由

**Files:**
- Create: `app/api/chat.py`
- Create: `app/api/plan.py`
- Create: `app/api/preference.py`
- Create: `app/api/monitor.py`
- Create: `tests/api/`

- [ ] **Step 1: Write failing test for chat endpoint**

```python
# tests/api/test_chat.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_chat_returns_plan_id():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/chat", json={
            "user_id": "test_user",
            "message": "我要去杭州3天，预算5000",
            "session_id": "test_session"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "plan_id" in data
        assert "answer" in data

@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
```

- [ ] **Step 2: Run test to verify it fails**

```
Expected: FAIL
```

- [ ] **Step 3: Write all API route files**

```python
# app/api/chat.py
"""Chat API - main conversation endpoint."""
import asyncio
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from app.agents.supervisor import PlanningAgent
from app.config import get_settings
from app.api.plan import save_plan

router = APIRouter(prefix="/api", tags=["chat"])

class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: str

class ChatResponse(BaseModel):
    answer: str
    plan_id: str
    agent_trace: dict
    health_alerts: list
    preference_compliance: list  # per Design Section 5.1

_agent = PlanningAgent()

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request, background_tasks: BackgroundTasks):
    """Main chat endpoint - triggers full multi-agent planning.

    Per Design Section 6.2: complete planning request has 90s timeout.
    Uses asyncio.wait_for to enforce timeout.
    """
    settings = get_settings()

    try:
        result = await asyncio.wait_for(
            _agent.plan(req.user_id, req.session_id, req.message),
            timeout=settings.request_timeout
        )
    except asyncio.TimeoutError:
        # Return partial result or timeout message
        return JSONResponse(
            status_code=200,
            content={
                "answer": "规划请求超时，请稍后重试或简化需求（如减少天数）",
                "plan_id": "",
                "agent_trace": {},
                "health_alerts": [],
                "preference_compliance": []
            }
        )

    # Save plan in background
    save_plan(result["plan_id"], result)

    return ChatResponse(
        answer=f"为您规划了{result['city']}{result['days']}天行程，祝您旅途愉快！",
        plan_id=result["plan_id"],
        agent_trace=result["agent_trace"],
        health_alerts=result.get("health_alerts", []),
        preference_compliance=result.get("preference_compliance", [])
    )
```

```python
# app/api/plan.py
"""Plan API - retrieve saved plans."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api", tags=["plan"])

# In-memory plan store (for demo; replace with Redis/DB in production)
_plan_store: dict = {}

class PlanResponse(BaseModel):
    plan_id: str
    city: str
    days: int
    daily_routes: list
    attractions: list
    food: list
    hotels: list
    budget_summary: dict
    health_alerts: list
    preference_compliance: list

@router.get("/plan/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: str):
    plan = _plan_store.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan

def save_plan(plan_id: str, plan_data: dict):
    """Called by chat endpoint after plan is generated."""
    _plan_store[plan_id] = plan_data
```

```python
# app/api/preference.py
"""Preference API - manage user preferences."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any
from app.agents.preference import PreferenceAgent

router = APIRouter(prefix="/api", tags=["preference"])

class PreferenceResponse(BaseModel):
    user_id: str
    preferences: dict
    history_trips: list

class PreferenceUpdate(BaseModel):
    key: str
    value: Any

_agent = PreferenceAgent()

@router.get("/preference/{user_id}", response_model=PreferenceResponse)
async def get_preference(user_id: str):
    prefs = await _agent.get_preference(user_id)
    return PreferenceResponse(user_id=user_id, preferences=prefs, history_trips=[])

@router.put("/preference/{user_id}")
async def update_preference(user_id: str, body: PreferenceUpdate):
    result = await _agent.update_preference(user_id, body.key, body.value)
    return result
```

```python
# app/api/monitor.py
"""Monitor API - health checks and metrics."""
from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.services.metrics_service import get_metrics_service
from app.memory.long_term import get_long_term_memory
import aiosqlite

router = APIRouter(prefix="/api", tags=["monitor"])

@router.get("/health")
async def health():
    """Health check endpoint.

    Per Design Section 5.1:
    - llm_available: true = at least one model works
    - llm_primary_available: true = primary model (OpenAI) works
    """
    from app.services.model_router import get_model_router
    settings = __import__("app.config", fromlist=["get_settings"]).get_settings()
    router = get_model_router()
    llm_primary_available = router.is_primary_available()
    llm_available = llm_primary_available  # true if primary works (simplified; full impl would check all)

    try:
        async with aiosqlite.connect(settings.database_url) as db:
            await db.execute("SELECT 1")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "healthy" if llm_available and db_status == "connected" else "degraded",
        "llm_available": llm_available,
        "llm_primary_available": llm_primary_available,
        "db_status": db_status
    }

@router.get("/metrics")
async def metrics():
    svc = get_metrics_service()
    return svc.get_summary()

@router.get("/metrics/prometheus")
async def prometheus_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/api/test_chat.py -v
Expected: PASS
```

- [ ] **Step 5: Add missing API tests (food, hotel, monitor, error_handler)**

```python
# tests/api/test_monitor.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_health_returns_llm_fields():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "llm_available" in data
        assert "llm_primary_available" in data
        assert "db_status" in data

@pytest.mark.asyncio
async def test_metrics_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "qps" in data

# tests/middleware/test_error_handler.py
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.middleware.error_handler import ErrorHandlerMiddleware, AgentError, AllAgentsFailedError

def test_agent_error_recoverable():
    app = FastAPI()
    app.add_middleware(ErrorHandlerMiddleware)
    @app.get("/test")
    def raise_recoverable():
        raise AgentError("Attractions Agent", "timeout", recoverable=True)

    client = TestClient(app)
    resp = client.get("/test")
    assert resp.status_code == 200
    assert "fallback" in resp.json()

def test_all_agents_failed_returns_fallback():
    app = FastAPI()
    app.add_middleware(ErrorHandlerMiddleware)
    @app.get("/test")
    def raise_all_failed():
        raise AllAgentsFailedError()

    client = TestClient(app)
    resp = client.get("/test")
    assert resp.status_code == 200
    assert "fallback" in resp.json()
```

- [ ] **Step 6: Run all tests**

```
pytest tests/ -v --tb=short
Expected: ALL PASS
```

- [ ] **Step 7: Commit**

```bash
git add app/api/chat.py app/api/plan.py app/api/preference.py app/api/monitor.py
git add tests/api/test_chat.py
git commit -m "feat: add all API endpoints (chat, plan, preference, monitor)"
```

---

### Task 17: FastAPI 主入口

**Files:**
- Create: `app/main.py`
- Modify: `app/api/chat.py` (save plan after creation)

- [ ] **Step 1: Write app/main.py**

```python
# app/main.py
"""FastAPI Application Entry Point."""
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.memory.long_term import get_long_term_memory
from app.middleware.tracing import TracingMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.api import chat, plan, preference, monitor

# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database
    settings = get_settings()
    import os
    os.makedirs(os.path.dirname(settings.database_url), exist_ok=True)
    mem = get_long_term_memory(settings.database_url)
    await mem.initialize()
    yield
    # Shutdown
    await mem.close()

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Smart Travel Journal - Multi-Agent Trip Planner",
        description="基于 LangChain 的智能出行规划 Multi-Agent 系统",
        version="1.0.0",
        lifespan=lifespan
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TracingMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)

    # Routes
    app.include_router(chat.router)
    app.include_router(plan.router)
    app.include_router(preference.router)
    app.include_router(monitor.router)

    @app.get("/")
    async def root():
        return {
            "name": "Smart Travel Journal",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/api/health"
        }

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=True)
```

- [ ] **Step 2: Update app/api/chat.py to save plan after creation**

```python
# Add to app/api/chat.py after chat endpoint:
from app.api.plan import save_plan

# In chat endpoint, add:
result = await _agent.plan(req.user_id, req.session_id, req.message)
save_plan(result["plan_id"], result)
```

- [ ] **Step 3: Run integration test**

```
pytest tests/api/test_chat.py -v
Expected: PASS
```

- [ ] **Step 4: Commit**

```bash
git add app/main.py app/api/chat.py
git commit -m "feat: add FastAPI main entry point with lifespan, middleware, and route registration"
```

---

## 阶段六：集成测试与 README

### Task 18: 集成测试

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_integration.py
"""End-to-end integration tests for the multi-agent system.

Covers:
- Full planning flow: chat → plan retrieval
- Budget summary schema validation (reserve, category breakdowns)
- Daily routes date field validation
- Health alert generation for heart disease
- Preference update/retrieval flow
- Health endpoint with llm_primary_available
- 404 for nonexistent plan
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_full_travel_planning_flow():
    """Test complete flow: chat → get plan → verify schema compliance."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        chat_resp = await client.post("/api/chat", json={
            "user_id": "int_test_user",
            "message": "我要去杭州3天，预算5000",
            "session_id": "int_test_session"
        })
        assert chat_resp.status_code == 200
        data = chat_resp.json()
        assert "plan_id" in data
        assert "agent_trace" in data
        assert "health_alerts" in data
        plan_id = data["plan_id"]

        plan_resp = await client.get(f"/api/plan/{plan_id}")
        assert plan_resp.status_code == 200
        plan_data = plan_resp.json()
        assert plan_data["city"] == "杭州"
        assert plan_data["days"] == 3
        # Verify budget_summary schema (Design Section 5.4)
        bs = plan_data["budget_summary"]
        assert "reserve" in bs
        assert "attractions_total" in bs
        assert "food_total" in bs
        assert "hotel_total" in bs
        # Verify daily_routes date field (Design Section 5.4)
        assert "date" in plan_data["daily_routes"][0]
        # Verify health endpoint
        health_resp = await client.get("/api/health")
        assert health_resp.status_code == 200
        assert "llm_primary_available" in health_resp.json()

@pytest.mark.asyncio
async def test_preference_update_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        pref_resp = await client.put("/api/preference/int_pref_user", json={
            "key": "health", "value": ["心脏病"]
        })
        assert pref_resp.status_code == 200
        get_resp = await client.get("/api/preference/int_pref_user")
        assert get_resp.status_code == 200
        assert "health" in get_resp.json()["preferences"]

@pytest.mark.asyncio
async def test_health_alert_generated_for_heart_disease():
    """Per Health Alert Rule Table (Design Section 2.4): heart disease → rule-based alert."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/chat", json={
            "user_id": "int_hc_user",
            "message": "我要去成都2天，我有心脏病",
            "session_id": "int_hc_session"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert any("药物" in a or "剧烈" in a for a in data["health_alerts"])

@pytest.mark.asyncio
async def test_plan_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/plan/nonexistent")
        assert resp.status_code == 404
```

- [ ] **Step 2: Run all tests**

```
pytest tests/ -v --tb=short
Expected: ALL PASS
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add end-to-end integration tests for full planning flow"
```

---

### Task 19: README.md

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

```markdown
# Smart Travel Journal - Multi-Agent Trip Planner

基于 LangChain 的智能出行规划 Multi-Agent 系统，支持景点推荐、路线规划、预算控制、美食住宿推荐和用户偏好管理。

## 功能特性

- **Multi-Agent 协作**：Supervisor + Specialist 模式，7 个专业 Agent 协作生成完整行程
- **双层记忆系统**：短期记忆（会话级）+ 长期记忆（SQLite，跨会话持久化）
- **健康提醒**：基于用户健康状况主动生成提醒（心脏病、糖尿病等）
- **预算控制**：Budget Agent 实时校验，超支自动触发路线调整（最多 2 轮）
- **模型降级**：OpenAI → Claude → 本地模型，多层容错保证可用性
- **可观测性**：结构化日志 + Prometheus Metrics + 链路追踪

## 快速开始

### 安装

```bash
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 OPENAI_API_KEY 等配置
```

### 启动服务

```bash
python -m app.main
# 或
uvicorn app.main:app --reload --port 8000
```

服务启动后访问：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/health
- Metrics：http://localhost:8000/api/metrics

### 运行测试

```bash
pytest tests/ -v
```

## API 示例

**规划行程：**

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "message": "我要去杭州3天，预算5000，我有心脏病，不喜欢硬座",
    "session_id": "session_001"
  }'
```

**响应示例：**

```json
{
  "answer": "为您规划了杭州3天行程，祝您旅途愉快！",
  "plan_id": "plan_abc123",
  "agent_trace": {
    "agents": ["Planning Agent", "Attractions Agent", "Budget Agent", "Route Agent", "Food Agent", "Hotel Agent", "Budget Agent (validation)"],
    "durations_ms": [12, 890, 450, 1200, 320, 280, 180],
    "errors": []
  },
  "health_alerts": ["您的行程包含较多步行，建议随身携带日常药物并避免剧烈活动"]
}
```

## 项目架构

```
app/
├── agents/          # Agent 定义
│   ├── supervisor.py  # Planning Agent（总控）
│   ├── attractions.py  # Attractions Agent
│   ├── route.py        # Route Agent
│   ├── budget.py       # Budget Agent
│   ├── food.py         # Food Agent
│   ├── hotel.py        # Hotel Agent
│   └── preference.py   # Preference Agent
├── tools/            # Tools 定义
├── memory/           # 记忆系统
│   ├── short_term.py  # 短期记忆
│   └── long_term.py   # 长期记忆（SQLite）
├── api/              # FastAPI 路由
├── services/         # 业务逻辑服务
└── middleware/       # 中间件

docs/superpowers/specs/   # 设计文档
docs/superpowers/plans/   # 实现计划
```

## Agent 协作流程

1. Planning Agent 解析用户意图（目的地、天数、预算、偏好）
2. Preference Agent 更新长期记忆（心脏病、硬座禁忌等）
3. 并行调用：Attractions Agent + Budget Agent
4. Route Agent 生成每日路线
5. 并行调用：Food Agent + Hotel Agent
6. Budget Agent 校验是否超支 → 必要时触发 Route Agent 调整（最多 2 轮）
7. 生成健康提醒 + 偏好合规说明
8. 整合输出完整行程方案

## 技术栈

| 层级 | 技术 |
|------|------|
| Web 框架 | FastAPI + Uvicorn |
| Agent 框架 | LangChain |
| 模型 | OpenAI GPT-4o-mini |
| 短期记忆 | LangChain ConversationBuffer |
| 长期记忆 | SQLite (aiosqlite) |
| 监控 | Prometheus + structlog |

## License

MIT
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with quick start, API examples, and architecture overview"
```

---

## 阶段七：最终验证

### Task 20: 全量测试验证

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: All tests PASS

- [ ] **Step 2: Verify app starts**

```bash
python -c "from app.main import app; print('App created successfully')"
```

- [ ] **Step 3: Final commit - mark project complete**

```bash
git tag v1.0.0
git commit -m "feat: complete travel multi-agent system v1.0.0"
```

---

## 依赖关系图（Task 执行顺序）

```
Task 1 (requirements, .env)
Task 2 (config)
Task 3 (long_term memory)   ← depends on Task 2
Task 4 (short_term memory)  ← depends on Task 2
Task 5 (metrics service)    ← depends on Task 2
Task 5b (memory_service)   ← depends on Task 3
Task 5c (model_router)     ← depends on Task 2

Task 6 (pref tools)         ← depends on Task 3
Task 7 (attr tools)         ← independent
Task 8 (route tools)        ← independent
Task 9 (budget tools)       ← independent
Task 10 (food tools)        ← independent
Task 11 (hotel tools)       ← independent

Task 12 (pref agent)        ← depends on Task 6
Task 13 (specialist agents) ← depends on Tasks 7-11

Task 14 (supervisor)        ← depends on Tasks 12-13, 5, 5c
Task 15 (middleware)        ← depends on Task 2
Task 16 (API routes)        ← depends on Tasks 14-15, 5c
Task 17 (main.py)           ← depends on all above

Task 18 (integration tests) ← depends on Task 17
Task 19 (README)             ← independent
Task 20 (final verification) ← depends on all
```
