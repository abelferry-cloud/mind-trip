# OpenClaw 双层动态提示词系统实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现完整的 Layer 1/2/3 三层动态提示词系统，替代并增强现有 `sys_prompt_builder.py`

**Architecture:** 新增 `app/graph/prompt/` 目录作为独立模块，包含 5 个 Python 文件 + `__init__.py`，各司其职通过 `PromptComposer` 组合。保留现有 `sys_prompt_builder.py` 作为向后兼容层。

**Tech Stack:** LangChain `Runnable` / `ChatPromptTemplate` / Python `pathlib` / 现有 `DailyLogManager` + `MarkdownMemoryManager`

---

## 文件结构概览

```
app/graph/prompt/
├── __init__.py              # 导出 PromptComposer, WorkspaceLoader, SystemPromptBuilder, MemoryLoader
├── config.py                # WORKSPACE_DIR, 文件列表常量
├── system_builder.py        # SystemPromptBuilder — Layer 1
├── workspace_loader.py       # WorkspaceLoader — Layer 2 (Runnable)
├── memory_loader.py          # MemoryLoader — Layer 3
└── composer.py               # PromptComposer (Runnable)

app/graph/sys_prompt_builder.py  # 保留，兼容层

tests/graph/prompt/
└── (对应测试文件)
```

---

## Task 1: `app/graph/prompt/config.py` — 路径与常量

**Files:**
- Create: `app/graph/prompt/config.py`

- [ ] **Step 1: 创建目录和基础文件**

```python
"""app/graph/prompt/config.py — Workspace 路径与文件常量。

参考 OpenClaw 的 workspace 文件布局：
- Layer 1: SYSTEM_PROMPT_<agent_name>.md
- Layer 2: SOUL.md / IDENTITY.md / USER.md / AGENTS.md / TOOLS.md / BOOTSTRAP.md
- Layer 2 (main only): MEMORY.md
- Layer 3: memory/YYYY-MM-DD.md
"""
from pathlib import Path

WORKSPACE_DIR = Path(__file__).parent.parent.parent / "workspace"

# Layer 1: System Prompt 文件命名模式
SYSTEM_PROMPT_FILE = "SYSTEM_PROMPT_{agent_name}.md"

# Layer 2: Workspace 核心文件（按加载顺序）
WORKSPACE_CORE_FILES = [
    "SOUL.md",
    "IDENTITY.md",
    "USER.md",
    "AGENTS.md",
    "TOOLS.md",
    "BOOTSTRAP.md",
]

# Layer 2: 仅主会话（main）加载
MAIN_SESSION_ONLY = ["MEMORY.md"]

# Layer 3: 每日 Memory 目录
MEMORY_DIR = WORKSPACE_DIR / "memory"
```

- [ ] **Step 2: 运行检查**

Run: `python -c "from app.graph.prompt.config import WORKSPACE_DIR, WORKSPACE_CORE_FILES; print(WORKSPACE_DIR, WORKSPACE_CORE_FILES)"`
Expected: `Path(...) ['SOUL.md', ...]`

---

## Task 2: `app/graph/prompt/system_builder.py` — Layer 1

**Files:**
- Create: `app/graph/prompt/system_builder.py`
- Test: `tests/graph/prompt/test_system_builder.py`

- [ ] **Step 1: 写测试**

```python
"""tests/graph/prompt/test_system_builder.py"""
import pytest
import tempfile
from pathlib import Path
from app.graph.prompt.system_builder import SystemPromptBuilder

@pytest.fixture
def temp_workspace(tmp_path):
    wp = tmp_path / "workspace"
    wp.mkdir()
    return wp

def test_load_existing_file(temp_workspace, monkeypatch):
    monkeypatch.setattr("app.graph.prompt.system_builder.WORKSPACE_DIR", temp_workspace)
    (temp_workspace / "SYSTEM_PROMPT_supervisor.md").write_text("---\ndate: 2026\n---\n你是一个主管 Agent", encoding="utf-8")
    sb = SystemPromptBuilder()
    result = sb.load("supervisor")
    assert "你是一个主管 Agent" in result
    assert "date: 2026" not in result  # frontmatter stripped

def test_load_nonexistent_file(temp_workspace, monkeypatch):
    monkeypatch.setattr("app.graph.prompt.system_builder.WORKSPACE_DIR", temp_workspace)
    sb = SystemPromptBuilder()
    result = sb.load("nonexistent_agent")
    assert result == ""

def test_load_file_without_frontmatter(temp_workspace, monkeypatch):
    monkeypatch.setattr("app.graph.prompt.system_builder.WORKSPACE_DIR", temp_workspace)
    (temp_workspace / "SYSTEM_PROMPT_attractions.md").write_text("你是一个景点 Agent", encoding="utf-8")
    sb = SystemPromptBuilder()
    result = sb.load("attractions")
    assert result == "你是一个景点 Agent"
```

- [ ] **Step 2: Run test — expect FAIL (file not found)**

Run: `pytest tests/graph/prompt/test_system_builder.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 创建 system_builder.py**

```python
"""app/graph/prompt/system_builder.py — Layer 1: System Prompt 加载器。

读取 workspace/SYSTEM_PROMPT_<agent_name>.md 作为 Layer 1。
文件不存在时返回空字符串，不抛异常。
"""
import re
from pathlib import Path

from app.graph.prompt.config import WORKSPACE_DIR, SYSTEM_PROMPT_FILE


def _strip_frontmatter(content: str) -> str:
    """去除 Markdown 文件头的 YAML frontmatter (---...--- 块)。"""
    pattern = r'^---\s*\n.*?\n---\s*\n?'
    return re.sub(pattern, "", content, flags=re.DOTALL).strip()


class SystemPromptBuilder:
    """加载 Agent 的 SYSTEM_PROMPT_<name>.md 文件。

    文件不存在时返回空字符串，不抛异常。
    """

    def load(self, agent_name: str) -> str:
        filepath = WORKSPACE_DIR / SYSTEM_PROMPT_FILE.format(agent_name=agent_name)
        if not filepath.exists():
            return ""
        try:
            return _strip_frontmatter(filepath.read_text(encoding="utf-8"))
        except Exception:
            return ""
```

- [ ] **Step 4: Run test — expect PASS**

Run: `pytest tests/graph/prompt/test_system_builder.py -v`
Expected: PASS

---

## Task 3: `app/graph/prompt/workspace_loader.py` — Layer 2

**Files:**
- Create: `app/graph/prompt/workspace_loader.py`
- Test: `tests/graph/prompt/test_workspace_loader.py`

- [ ] **Step 1: 写测试**

```python
"""tests/graph/prompt/test_workspace_loader.py"""
import pytest
from pathlib import Path
from app.graph.prompt.workspace_loader import WorkspaceLoader
from app.graph.prompt.config import WORKSPACE_DIR

@pytest.fixture
def temp_workspace(tmp_path, monkeypatch):
    wp = tmp_path / "workspace"
    wp.mkdir()
    monkeypatch.setattr("app.graph.prompt.workspace_loader.WORKSPACE_DIR", wp)
    return wp

def test_loads_core_files_in_order(temp_workspace, monkeypatch):
    monkeypatch.setattr("app.graph.prompt.workspace_loader.WORKSPACE_DIR", temp_workspace)
    # 创建部分 workspace 文件
    (temp_workspace / "SOUL.md").write_text("Soul content", encoding="utf-8")
    (temp_workspace / "AGENTS.md").write_text("Agents content", encoding="utf-8")
    (temp_workspace / "USER.md").write_text("User content", encoding="utf-8")
    # BOOTSTRAP.md 不存在

    loader = WorkspaceLoader(mode="shared")
    result = loader.invoke({})

    assert "## SOUL" in result["workspace_prompt"]
    assert "## AGENTS" in result["workspace_prompt"]
    assert "## USER" in result["workspace_prompt"]
    assert "## BOOTSTRAP" not in result["workspace_prompt"]  # 不存在则跳过
    assert "MEMORY.md" not in result["workspace_prompt"]  # shared 模式不加载

def test_main_mode_includes_memory_md(temp_workspace, monkeypatch):
    monkeypatch.setattr("app.graph.prompt.workspace_loader.WORKSPACE_DIR", temp_workspace)
    (temp_workspace / "SOUL.md").write_text("Soul", encoding="utf-8")
    (temp_workspace / "MEMORY.md").write_text("Memory content", encoding="utf-8")

    loader = WorkspaceLoader(mode="main")
    result = loader.invoke({})

    assert "## MEMORY" in result["workspace_prompt"]

def test_session_mode_override_in_invoke(temp_workspace, monkeypatch):
    monkeypatch.setattr("app.graph.prompt.workspace_loader.WORKSPACE_DIR", temp_workspace)
    (temp_workspace / "SOUL.md").write_text("Soul", encoding="utf-8")
    (temp_workspace / "MEMORY.md").write_text("Memory content", encoding="utf-8")

    loader = WorkspaceLoader(mode="shared")  # 初始化为 shared
    result = loader.invoke({"session_mode": "main"})  # 但调用时覆盖为 main

    assert "## MEMORY" in result["workspace_prompt"]  # main 模式应加载 MEMORY

def test_returns_workspace_loaded_at_timestamp(temp_workspace, monkeypatch):
    monkeypatch.setattr("app.graph.prompt.workspace_loader.WORKSPACE_DIR", temp_workspace)
    (temp_workspace / "SOUL.md").write_text("Soul", encoding="utf-8")

    loader = WorkspaceLoader()
    result = loader.invoke({})
    assert "workspace_loaded_at" in result
    assert "T" in result["workspace_loaded_at"]  # ISO format
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `pytest tests/graph/prompt/test_workspace_loader.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 创建 workspace_loader.py**

```python
"""app/graph/prompt/workspace_loader.py — Layer 2: Workspace 动态加载器。

LangChain Runnable — 每次 invoke 动态加载 Layer 2 文件。
遵循 OpenClaw 的上下文分层：
- SOUL / IDENTITY / USER / AGENTS / TOOLS / BOOTSTRAP 始终加载
- MEMORY.md 仅在 mode="main" 时注入
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from langchain_core.runnables import Runnable

from app.graph.prompt.config import WORKSPACE_DIR, WORKSPACE_CORE_FILES, MAIN_SESSION_ONLY


def _strip_frontmatter(content: str) -> str:
    pattern = r'^---\s*\n.*?\n---\s*\n?'
    return re.sub(pattern, "", content, flags=re.DOTALL).strip()


def _read_workspace_file(filename: str) -> Optional[str]:
    """读取 workspace 目录下的 .md 文件，返回剥离 frontmatter 后的内容。

    文件不存在或读取失败时返回 None。
    """
    filepath = WORKSPACE_DIR / filename
    if not filepath.exists():
        return None
    try:
        return _strip_frontmatter(filepath.read_text(encoding="utf-8"))
    except Exception:
        return None


def _section_block(title: str, content: str) -> str:
    """将内容包装为带标题的 Markdown 区块。"""
    return f"\n## {title}\n\n{content}\n"


class WorkspaceLoader(Runnable):
    """LangChain Runnable — 每次 invoke 动态加载 Layer 2 文件。"""

    def __init__(self, mode: Literal["main", "shared"] = "shared"):
        self.mode = mode

    def invoke(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """LangChain Runnable.invoke().

        Args:
            input: 支持 session_mode 覆盖初始化时的 mode

        Returns:
            {"workspace_prompt": str, "workspace_loaded_at": ISO datetime}
        """
        mode = input.get("session_mode", self.mode)
        file_order = WORKSPACE_CORE_FILES + (MAIN_SESSION_ONLY if mode == "main" else [])

        prompt_parts = []
        for filename in file_order:
            content = _read_workspace_file(filename)
            if content is None:
                continue
            section_name = filename.replace(".md", "")
            prompt_parts.append(_section_block(section_name, content))

        workspace_prompt = "\n".join(prompt_parts)
        return {
            "workspace_prompt": workspace_prompt,
            "workspace_loaded_at": datetime.now().isoformat(),
        }
```

- [ ] **Step 4: Run test — expect PASS**

Run: `pytest tests/graph/prompt/test_workspace_loader.py -v`
Expected: PASS

---

## Task 4: `app/graph/prompt/memory_loader.py` — Layer 3

**Files:**
- Create: `app/graph/prompt/memory_loader.py`
- Test: `tests/graph/prompt/test_memory_loader.py`

- [ ] **Step 1: 写测试**

```python
"""tests/graph/prompt/test_memory_loader.py"""
import pytest
from pathlib import Path
from app.graph.prompt.memory_loader import MemoryLoader

@pytest.fixture
def temp_workspace(tmp_path):
    mem_dir = tmp_path / "memory"
    mem_dir.mkdir()
    mem_file = tmp_path / "MEMORY.md"
    return {"mem_dir": mem_dir, "mem_file": mem_file}

def test_load_combines_daily_and_memory(temp_workspace):
    from app.memory.daily_log import DailyLogManager
    from app.memory.markdown_memory import MarkdownMemoryManager
    dl_mgr = DailyLogManager(memory_dir=temp_workspace["mem_dir"])
    mem_mgr = MarkdownMemoryManager(memory_path=temp_workspace["mem_file"])
    loader = MemoryLoader(dl_mgr, mem_mgr)

    dl_mgr.append("sess_001", "user_001", "hello", "hi")
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        mem_mgr.update_preference("user_001", "spending_style", "节省")
    )

    result = loader.load("user_001", "sess_001", mode="main")
    assert "hello" in result
    assert "节省" in result

def test_shared_mode_skips_memory(temp_workspace):
    from app.memory.daily_log import DailyLogManager
    from app.memory.markdown_memory import MarkdownMemoryManager
    dl_mgr = DailyLogManager(memory_dir=temp_workspace["mem_dir"])
    mem_mgr = MarkdownMemoryManager(memory_path=temp_workspace["mem_file"])
    loader = MemoryLoader(dl_mgr, mem_mgr)

    dl_mgr.append("sess_001", "user_001", "hello", "hi")
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        mem_mgr.update_preference("user_001", "spending_style", "节省")
    )

    result = loader.load("user_001", "sess_001", mode="shared")
    assert "hello" in result
    assert "节省" not in result  # MEMORY.md skipped in shared mode

def test_enforce_budget_truncates_long_memory(temp_workspace):
    from app.memory.daily_log import DailyLogManager
    from app.memory.markdown_memory import MarkdownMemoryManager
    dl_mgr = DailyLogManager(memory_dir=temp_workspace["mem_dir"])
    mem_mgr = MarkdownMemoryManager(memory_path=temp_workspace["mem_file"])
    # max_chars=200 足够小，强制触发截断
    loader = MemoryLoader(dl_mgr, mem_mgr, max_chars=200)

    # 写入大量 MEMORY 内容
    long_content = "x" * 500
    mem_mgr.memory_path.write_text(f"# MEMORY\n\n{long_content}", encoding="utf-8")
    dl_mgr.append("sess_001", "user_001", "hello", "hi")

    result = loader.load("user_001", "sess_001", mode="main")
    assert len(result) <= 200 + 50  # 允许一些 sentinel 开销
    assert "..." in result or "截断" in result  # 截断标记存在

def test_enforce_budget_preserves_short_content(temp_workspace):
    from app.memory.daily_log import DailyLogManager
    from app.memory.markdown_memory import MarkdownMemoryManager
    dl_mgr = DailyLogManager(memory_dir=temp_workspace["mem_dir"])
    mem_mgr = MarkdownMemoryManager(memory_path=temp_workspace["mem_file"])
    loader = MemoryLoader(dl_mgr, mem_mgr, max_chars=8000)

    dl_mgr.append("sess_001", "user_001", "hi", "hello")

    result = loader.load("user_001", "sess_001", mode="main")
    assert "hi" in result
    assert "hello" in result
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `pytest tests/graph/prompt/test_memory_loader.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 创建 memory_loader.py**

```python
"""app/graph/prompt/memory_loader.py — Layer 3: Session Memory 加载器。

加载 Layer 3: 今日+昨日日志 + (仅 main) MEMORY.md。
组合为 "## Memory" 区段字符串。

Token 预算控制由本类负责：分阶段截断直到在预算内。
"""
from typing import Literal, Optional

from app.memory.daily_log import DailyLogManager
from app.memory.markdown_memory import MarkdownMemoryManager


class MemoryLoader:
    """加载 Layer 3: 今日+昨日日志 + (仅 main) MEMORY.md。

    组合为 "## Memory" 区段字符串。

    Token 预算控制由本类负责：分阶段截断直到在预算内
    （先截断 MEMORY.md，再截断较旧的日志条目）。
    使用字符数近似控制（1 token ≈ 4 字符），不调用外部 token 计数库。
    """

    def __init__(
        self,
        daily_log_manager: Optional[DailyLogManager] = None,
        memory_manager: Optional[MarkdownMemoryManager] = None,
        max_chars: int = 8000,  # ~2,000 tokens
    ):
        self._daily_log_manager = daily_log_manager or DailyLogManager()
        self._memory_manager = memory_manager or MarkdownMemoryManager()
        self._max_chars = max_chars

    def load(
        self,
        user_id: str,
        session_id: str,
        mode: Literal["main", "shared"] = "main",
    ) -> str:
        """加载会话记忆并组合为 markdown 字符串。

        - 日志（今日 + 昨日）始终加载
        - MEMORY.md 仅在 main 模式下加载
        """
        parts = []

        # 今日 + 昨日日志
        daily_content = self._daily_log_manager.read_today_and_yesterday()
        if daily_content:
            parts.append(f"## 今日与昨日会话日志\n\n{daily_content}")

        # 长期记忆 — 仅 main
        if mode == "main":
            memory_content = self._memory_manager.get_memory()
            if memory_content:
                parts.append(f"## 长期记忆 (MEMORY.md)\n\n{memory_content}")

        # Token 预算控制：分阶段截断
        combined = self._enforce_budget(parts, self._max_chars)
        return combined

    def _enforce_budget(self, parts: list[str], max_chars: int) -> str:
        """分阶段截断直到符合字符预算。"""
        if not parts:
            return ""

        # 先尝试直接组合
        combined = "\n\n".join(parts)
        if len(combined) <= max_chars:
            return combined

        # 阶段 1: MEMORY.md 截断（假设它在 parts[-1]）
        if len(parts) > 1 and len(parts[-1]) > max_chars // 2:
            memory_part = parts[-1]
            header_end = memory_part.index("\n\n") + 2 if "\n\n" in memory_part else 0
            memory_body = memory_part[header_end:]
            truncated_body = memory_body[: max_chars // 2] + "\n\n[... MEMORY.md 内容已截断]"
            parts[-1] = memory_part[:header_end] + truncated_body
            combined = "\n\n".join(parts)
            if len(combined) <= max_chars:
                return combined

        # 阶段 2: 较旧日志截断（从头开始，逐条移除直到符合预算）
        result_parts = list(parts)
        while len(result_parts) > 1 and len("\n\n".join(result_parts)) > max_chars:
            result_parts.pop(0)  # 移除最旧的日志
        combined = "\n\n".join(result_parts)

        # 阶段 3: 硬截断
        if len(combined) > max_chars:
            combined = combined[:max_chars] + "\n\n[... 内容已截断以符合 token 预算]"

        return combined
```

- [ ] **Step 4: Run test — expect PASS**

Run: `pytest tests/graph/prompt/test_memory_loader.py -v`
Expected: PASS

---

## Task 5: `app/graph/prompt/composer.py` — PromptComposer

**Files:**
- Create: `app/graph/prompt/composer.py`
- Test: `tests/graph/prompt/test_composer.py`

- [ ] **Step 1: 写测试**

```python
"""tests/graph/prompt/test_composer.py"""
import pytest
from pathlib import Path
from app.graph.prompt.composer import PromptComposer

@pytest.fixture
def temp_workspace(tmp_path, monkeypatch):
    wp = tmp_path / "workspace"
    wp.mkdir()
    mem_dir = wp / "memory"
    mem_dir.mkdir()
    mem_file = wp / "MEMORY.md"
    monkeypatch.setattr("app.graph.prompt.config.WORKSPACE_DIR", wp)
    monkeypatch.setattr("app.graph.prompt.config.MEMORY_DIR", mem_dir)
    return {"workspace": wp, "mem_dir": mem_dir, "mem_file": mem_file}

def test_compose_combines_three_layers(temp_workspace):
    from app.memory.daily_log import DailyLogManager
    from app.memory.markdown_memory import MarkdownMemoryManager
    from app.graph.prompt.memory_loader import MemoryLoader
    from app.graph.prompt.workspace_loader import WorkspaceLoader
    from app.graph.prompt.system_builder import SystemPromptBuilder

    # 创建 workspace 文件
    (temp_workspace["workspace"] / "SYSTEM_PROMPT_supervisor.md").write_text("Supervisor system prompt", encoding="utf-8")
    (temp_workspace["workspace"] / "SOUL.md").write_text("Soul content", encoding="utf-8")
    (temp_workspace["workspace"] / "AGENTS.md").write_text("Agents content", encoding="utf-8")
    (temp_workspace["mem_file"]).write_text("Memory content", encoding="utf-8")

    # 创建 daily log
    dl_mgr = DailyLogManager(memory_dir=temp_workspace["mem_dir"])
    mem_mgr = MarkdownMemoryManager(memory_path=temp_workspace["mem_file"])
    dl_mgr.append("sess_001", "user_001", "hello", "hi")

    # 直接测试 Composer 内部组合逻辑
    from app.graph.prompt.system_builder import SystemPromptBuilder
    from app.graph.prompt.workspace_loader import WorkspaceLoader
    from app.graph.prompt.memory_loader import MemoryLoader

    composer = PromptComposer(agent_name="supervisor", agent_type="Planning", mode="main")
    composer._system_builder = SystemPromptBuilder()
    composer._workspace_loader = WorkspaceLoader(mode="main")
    composer._memory_loader = MemoryLoader(dl_mgr, mem_mgr)

    result = composer.invoke({"user_id": "user_001", "session_id": "sess_001"})

    assert "Supervisor system prompt" in result["system_prompt"]
    assert "Soul content" in result["system_prompt"]
    assert "hello" in result["system_prompt"]
    assert "Memory content" in result["system_prompt"]
    assert result["agent_name"] == "supervisor"
    assert result["mode"] == "main"

def test_shared_mode_skips_memory(temp_workspace):
    from app.memory.daily_log import DailyLogManager
    from app.memory.markdown_memory import MarkdownMemoryManager
    from app.graph.prompt.memory_loader import MemoryLoader
    from app.graph.prompt.workspace_loader import WorkspaceLoader
    from app.graph.prompt.system_builder import SystemPromptBuilder

    (temp_workspace["workspace"] / "SYSTEM_PROMPT_supervisor.md").write_text("Supervisor system prompt", encoding="utf-8")
    (temp_workspace["workspace"] / "SOUL.md").write_text("Soul content", encoding="utf-8")
    (temp_workspace["mem_file"]).write_text("Memory content", encoding="utf-8")

    dl_mgr = DailyLogManager(memory_dir=temp_workspace["mem_dir"])
    mem_mgr = MarkdownMemoryManager(memory_path=temp_workspace["mem_file"])
    dl_mgr.append("sess_001", "user_001", "hello", "hi")

    composer = PromptComposer(agent_name="supervisor", agent_type="Planning", mode="shared")
    composer._system_builder = SystemPromptBuilder()
    composer._workspace_loader = WorkspaceLoader(mode="shared")
    composer._memory_loader = MemoryLoader(dl_mgr, mem_mgr)

    result = composer.invoke({"user_id": "user_001", "session_id": "sess_001"})

    assert "Memory content" not in result["system_prompt"]  # shared 跳过 MEMORY
    assert "hello" in result["system_prompt"]  # 日志仍加载

def test_invoker_session_mode_override(temp_workspace):
    from app.memory.daily_log import DailyLogManager
    from app.memory.markdown_memory import MarkdownMemoryManager

    (temp_workspace["workspace"] / "SYSTEM_PROMPT_supervisor.md").write_text("Supervisor", encoding="utf-8")
    (temp_workspace["workspace"] / "SOUL.md").write_text("Soul", encoding="utf-8")
    (temp_workspace["mem_file"]).write_text("Memory content", encoding="utf-8")

    dl_mgr = DailyLogManager(memory_dir=temp_workspace["mem_dir"])
    mem_mgr = MarkdownMemoryManager(memory_path=temp_workspace["mem_file"])

    composer = PromptComposer(agent_name="supervisor", mode="shared")  # 初始化为 shared
    composer._system_builder = SystemPromptBuilder()
    composer._workspace_loader = WorkspaceLoader(mode="shared")
    composer._memory_loader = MemoryLoader(dl_mgr, mem_mgr)

    # 但调用时覆盖为 main
    result = composer.invoke({"user_id": "user_001", "session_id": "sess_001", "session_mode": "main"})
    assert "Memory content" in result["system_prompt"]  # main 模式覆盖
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `pytest tests/graph/prompt/test_composer.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 创建 composer.py**

```python
"""app/graph/prompt/composer.py — PromptComposer: 三层 Prompt 组合器。

LangChain Runnable — 协调 Layer 1/2/3 的加载顺序，组合为最终 prompt 字符串。
"""
from datetime import datetime
from typing import Any, Dict, Literal

from langchain_core.runnables import Runnable

from app.graph.prompt.system_builder import SystemPromptBuilder
from app.graph.prompt.workspace_loader import WorkspaceLoader
from app.graph.prompt.memory_loader import MemoryLoader


class PromptComposer(Runnable):
    """三层 Prompt 组合器（LangChain Runnable）。

    使用方式（嵌入 LCEL 链）:
        composer = PromptComposer(agent_name="Supervisor", agent_type="...", mode="main")
        chain = composer | chat_model | output_parser
    """

    def __init__(
        self,
        agent_name: str,
        agent_type: str = "",
        mode: Literal["main", "shared"] = "main",
    ):
        self.agent_name = agent_name
        self.agent_type = agent_type
        self.mode = mode
        self._system_builder = SystemPromptBuilder()
        self._workspace_loader = WorkspaceLoader(mode=mode)
        self._memory_loader = MemoryLoader()

    def invoke(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """组合三层 Prompt。

        Args:
            input: 包含 user_id, session_id, 以及其他动态上下文

        Returns:
            {
                "system_prompt": str,
                "agent_name": str,
                "agent_type": str,
                "mode": str,
                "workspace_loaded_at": ISO datetime,
            }
        """
        user_id = input.get("user_id", "")
        session_id = input.get("session_id", "")
        mode = input.get("session_mode", self.mode)

        # Layer 1: System Prompt
        layer1 = self._system_builder.load(self.agent_name)

        # Layer 2: Workspace
        layer2_result = self._workspace_loader.invoke({"session_mode": mode})
        layer2 = layer2_result["workspace_prompt"]

        # Layer 3: Memory
        layer3 = self._memory_loader.load(user_id, session_id, mode)

        # 组合
        parts = []
        if layer1:
            parts.append(f"## System Prompt\n\n{layer1}")
        if layer2:
            parts.append(f"## Workspace Context\n\n{layer2}")
        if layer3:
            parts.append(f"## Memory\n\n{layer3}")

        system_prompt = "\n\n".join(parts)

        return {
            "system_prompt": system_prompt,
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "mode": mode,
            "workspace_loaded_at": datetime.now().isoformat(),
        }

    def batch(self, inputs: list, **kwargs) -> list:
        return [self.invoke(i, **kwargs) for i in inputs]

    def stream(self, input, **kwargs):
        yield self.invoke(input, **kwargs)
```

- [ ] **Step 4: Run test — expect PASS**

Run: `pytest tests/graph/prompt/test_composer.py -v`
Expected: PASS

---

## Task 6: `app/graph/prompt/__init__.py` — 导出模块

**Files:**
- Create: `app/graph/prompt/__init__.py`

- [ ] **Step 1: 创建 __init__.py**

```python
"""app/graph/prompt — OpenClaw 三层动态提示词系统。

模块结构：
- config: 路径与文件常量
- system_builder: Layer 1 — System Prompt 加载
- workspace_loader: Layer 2 — Workspace 动态加载（LangChain Runnable）
- memory_loader: Layer 3 — Session Memory 加载
- composer: PromptComposer — 三层组合器（LangChain Runnable）
"""
from app.graph.prompt.config import (
    WORKSPACE_DIR,
    MEMORY_DIR,
    WORKSPACE_CORE_FILES,
    MAIN_SESSION_ONLY,
)
from app.graph.prompt.system_builder import SystemPromptBuilder
from app.graph.prompt.workspace_loader import WorkspaceLoader
from app.graph.prompt.memory_loader import MemoryLoader
from app.graph.prompt.composer import PromptComposer

__all__ = [
    "PromptComposer",
    "WorkspaceLoader",
    "MemoryLoader",
    "SystemPromptBuilder",
    "WORKSPACE_DIR",
    "MEMORY_DIR",
    "WORKSPACE_CORE_FILES",
    "MAIN_SESSION_ONLY",
]
```

- [ ] **Step 2: 验证导入**

Run: `python -c "from app.graph.prompt import PromptComposer, WorkspaceLoader, MemoryLoader, SystemPromptBuilder; print('OK')"`
Expected: `OK`

---

## Task 7: `app/graph/sys_prompt_builder.py` — 兼容层

**Files:**
- Modify: `app/graph/sys_prompt_builder.py`

- [ ] **Step 1: 读取现有文件，保留向后兼容接口**

现有 `sys_prompt_builder.py` 的 `get_supervisor_loader()` 等工厂函数被 `supervisor.py` 和 `chat_service.py` 使用。将内部实现替换为 `PromptComposer`，但保持函数签名不变。

```python
"""app/graph/sys_prompt_builder.py — 向后兼容层。

内部已迁移至 app.graph.prompt 模块。本文件保留以确保
现有调用方（supervisor.py, chat_service.py）无需修改。
"""
from typing import Dict, Any, Literal, Optional

from app.graph.prompt.composer import PromptComposer


def get_supervisor_loader(
    mode: Literal["main", "shared"] = "main",
    context: Optional[Dict[str, Any]] = None,
) -> PromptComposer:
    return PromptComposer(
        agent_name="Supervisor",
        agent_type="Planning Coordinator — 协调所有专家 Agent 完成旅行规划",
        mode=mode,
    )


def get_attractions_loader(
    mode: Literal["main", "shared"] = "main",
    context: Optional[Dict[str, Any]] = None,
) -> PromptComposer:
    return PromptComposer(
        agent_name="Attractions",
        agent_type="Attractions Specialist — 搜索和推荐旅行景点",
        mode=mode,
    )


def get_food_loader(
    mode: Literal["main", "shared"] = "main",
    context: Optional[Dict[str, Any]] = None,
) -> PromptComposer:
    return PromptComposer(
        agent_name="Food",
        agent_type="Food Specialist — 推荐当地美食和餐厅",
        mode=mode,
    )


def get_hotel_loader(
    mode: Literal["main", "shared"] = "main",
    context: Optional[Dict[str, Any]] = None,
) -> PromptComposer:
    return PromptComposer(
        agent_name="Hotel",
        agent_type="Hotel Specialist — 搜索和推荐住宿",
        mode=mode,
    )


def get_budget_loader(
    mode: Literal["main", "shared"] = "main",
    context: Optional[Dict[str, Any]] = None,
) -> PromptComposer:
    return PromptComposer(
        agent_name="Budget",
        agent_type="Budget Specialist — 计算和验证旅行预算",
        mode=mode,
    )


def get_route_loader(
    mode: Literal["main", "shared"] = "main",
    context: Optional[Dict[str, Any]] = None,
) -> PromptComposer:
    return PromptComposer(
        agent_name="Route",
        agent_type="Route Planner — 规划每日行程路线",
        mode=mode,
    )


def get_preference_loader(
    mode: Literal["main", "shared"] = "main",
    context: Optional[Dict[str, Any]] = None,
) -> PromptComposer:
    return PromptComposer(
        agent_name="Preference",
        agent_type="Preference Analyst — 解析和更新用户偏好",
        mode=mode,
    )


# 保留的底层函数
from app.graph.prompt.config import WORKSPACE_DIR
from app.graph.prompt.workspace_loader import WorkspaceLoader
from app.graph.prompt.memory_loader import MemoryLoader


def build_workspace_prompt_loader(
    mode: Literal["main", "shared"] = "main",
    agent_name: str = "Agent",
    agent_type: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> PromptComposer:
    return PromptComposer(
        mode=mode,
        agent_name=agent_name,
        agent_type=agent_type,
    )


def build_session_prompt(mode: Literal["main", "shared"] = "main") -> str:
    from app.graph.prompt.system_builder import SystemPromptBuilder
    from app.graph.prompt.workspace_loader import WorkspaceLoader
    from app.graph.prompt.memory_loader import MemoryLoader

    sb = SystemPromptBuilder()
    wl = WorkspaceLoader(mode=mode)
    ml = MemoryLoader()

    layer1 = sb.load("Agent")
    layer2 = wl.invoke({"session_mode": mode})["workspace_prompt"]
    layer3 = ml.load("", "", mode)

    parts = []
    if layer1:
        parts.append(f"## System Prompt\n\n{layer1}")
    if layer2:
        parts.append(f"## Workspace Context\n\n{layer2}")
    if layer3:
        parts.append(f"## Memory\n\n{layer3}")

    return "\n\n".join(parts)


def build_core_prompt() -> str:
    return build_session_prompt(mode="shared")


def build_main_session_prompt() -> str:
    return build_session_prompt(mode="main")
```

- [ ] **Step 2: 验证兼容层工作**

Run: `python -c "from app.graph.sys_prompt_builder import get_supervisor_loader; p = get_supervisor_loader('main'); r = p.invoke({'user_id': 'test', 'session_id': 'sess'}); print('system_prompt length:', len(r['system_prompt']))"`
Expected: 输出非零长度的 system_prompt

---

## Task 8: 创建 SYSTEM_PROMPT_*.md 文件

**Files:**
- Create: `workspace/SYSTEM_PROMPT_supervisor.md`
- Create: `workspace/SYSTEM_PROMPT_attractions.md`
- Create: `workspace/SYSTEM_PROMPT_budget.md`
- Create: `workspace/SYSTEM_PROMPT_route.md`
- Create: `workspace/SYSTEM_PROMPT_food.md`
- Create: `workspace/SYSTEM_PROMPT_hotel.md`
- Create: `workspace/SYSTEM_PROMPT_preference.md`

- [ ] **Step 1: 创建 SYSTEM_PROMPT_supervisor.md**

```markdown
# Supervisor Agent — Layer 1 System Prompt

## 角色定位

你是旅行规划主管 Agent，负责协调多个专家 Agent 完成完整的旅行规划。
你拥有以下专家团队：景点 Agent、路线 Agent、预算 Agent、美食 Agent、酒店 Agent、偏好 Agent。

## 能力边界

**你可以：**
- 调用各专家 Agent 获取信息
- 综合各方建议生成完整旅行方案
- 根据用户偏好和预算约束调整方案

**你不能：**
- 代替用户做出预订决策
- 访问外部支付接口
- 泄露用户的个人信息给第三方

## 安全规则

- 未经用户明确确认，不执行任何涉及金钱的操作
- 拒绝任何破坏性请求
- 有疑问时先询问，再行动

## 工具指令

使用 agent_trace 追踪整个规划流程，便于调试和问题排查。
```

（其他 Agent 的 SYSTEM_PROMPT_*.md 文件类似结构，聚焦于各自的专业领域）

- [ ] **Step 2: 验证所有文件创建成功**

Run: `ls workspace/SYSTEM_PROMPT_*.md`
Expected: 列出 7 个文件

---

## Task 9: 运行全部测试

- [ ] **Step 1: 运行所有新测试**

Run: `pytest tests/graph/prompt/ -v`
Expected: ALL PASS

- [ ] **Step 2: 运行现有相关测试确保未破坏**

Run: `pytest tests/memory/test_injector.py -v`
Expected: PASS

---

## Task 10: 提交

- [ ] **Commit**

```bash
git add app/graph/prompt/ app/graph/sys_prompt_builder.py workspace/SYSTEM_PROMPT_*.md tests/graph/
git commit -m "feat(prompt): implement OpenClaw 3-layer dynamic prompt system

- app/graph/prompt/: new modular prompt loaders (Layer 1/2/3)
- PromptComposer: LangChain Runnable combining all 3 layers
- SystemPromptBuilder: Layer 1 loading from SYSTEM_PROMPT_<agent>.md
- WorkspaceLoader: Layer 2 loading from SOUL/USER/AGENTS/etc
- MemoryLoader: Layer 3 loading with token budget enforcement
- Backward compat: sys_prompt_builder.py updated to use new modules
- 7 SYSTEM_PROMPT_*.md files for each agent"
```
