# OpenClaw 双层动态提示词系统设计

**日期**: 2026-03-29
**目标**: 参考 OpenClaw 的 Layer 1/2/3 上下文分层架构，使用 LangChain 实现动态提示词加载

---

## 1. 背景与目标

当前 `app/graph/sys_prompt_builder.py` 仅实现了 Layer 2（Workspace），缺少 Layer 1（System Prompt）和 Layer 3（Session Memory）的统一集成。本设计旨在实现完整的双层提示词系统：

- **Layer 1**: System Prompt — 角色定位 / 能力边界 / 安全规则 / 工具指令（~8,000-12,000 tokens）
- **Layer 2**: Workspace 注入层 — SOUL / USER / AGENTS / IDENTITY / TOOLS / BOOTSTRAP（~2,000-6,000 tokens）
- **Layer 3**: Session Memory — memory/YYYY-MM-DD.md + MEMORY.md（~60% token 预算）
  - **Token 预算控制**: 由 `MemoryLoader` 负责，分阶段截断：
  1. 先截断 MEMORY.md 内容（精选内容，优先保留）
  2. 若仍超预算，再截断较旧的日志条目
  3. 使用字符数近似控制（1 token ≈ 4 字符），不调用外部 token 计数库

---

## 2. 文件结构

```
app/graph/prompt/
├── __init__.py              # 导出 PromptComposer 及主要类
├── config.py                # 文件路径配置、加载顺序常量
├── system_builder.py        # SystemPromptBuilder — Layer 1
├── workspace_loader.py       # WorkspaceLoader — Layer 2 (LangChain Runnable)
├── memory_loader.py          # MemoryLoader — Layer 3
├── composer.py               # PromptComposer — 三层组合器 (LangChain Runnable)

app/graph/sys_prompt_builder.py  # 保留，向后兼容
```

---

## 3. 各组件设计

### 3.1 `config.py` — 路径与常量

```python
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

### 3.2 `system_builder.py` — Layer 1

```python
class SystemPromptBuilder:
    """加载 Agent 的 SYSTEM_PROMPT_<name>.md 文件。

    文件不存在时返回空字符串，不抛异常。
    """

    def load(agent_name: str) -> str:
        filepath = WORKSPACE_DIR / f"SYSTEM_PROMPT_{agent_name}.md"
        if not filepath.exists():
            return ""
        return _strip_frontmatter(filepath.read_text(encoding="utf-8"))
```

**职责**: 读取 `workspace/SYSTEM_PROMPT_{agent_name}.md` 作为 Layer 1。

### 3.3 `workspace_loader.py` — Layer 2

```python
class WorkspaceLoader(Runnable):
    """LangChain Runnable — 每次 invoke 动态加载 Layer 2 文件。

    遵循 OpenClaw 的上下文分层：
    - SOUL / IDENTITY / USER / AGENTS / TOOLS / BOOTSTRAP 始终加载
    - MEMORY.md 仅在 mode="main" 时注入
    """

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
        # 按 file_order 加载文件，组装为 ## {filename} 区块
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

**职责**: 作为 LangChain Runnable，每次调用动态读取 workspace 文件。

### 3.4 `memory_loader.py` — Layer 3

```python
from typing import Literal, Optional

class MemoryLoader:
    """加载 Layer 3: 今日+昨日日志 + (仅 main) MEMORY.md。

    组合为 "## Memory" 区段字符串。

    Token 预算控制由本类负责：按顺序截断直到在预算内
    （先截断 MEMORY.md，再截断较旧的日志条目）。
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
        # 1. MEMORY.md 截断（精选内容，优先保留较少）
        # 2. 较旧日志条目截断
        # 3. 最终硬截断
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
            # MEMORY.md 太长，截断其内容部分（跳过标题行）
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

**职责**: 组合 Layer 3 内容，内部使用现有组件：
- `DailyLogManager`（`app/memory/daily_log.py`）
- `MarkdownMemoryManager`（`app/memory/markdown_memory.py`）

### 3.5 `composer.py` — PromptComposer

```python
class PromptComposer(Runnable):
    """三层 Prompt 组合器（LangChain Runnable）。

    compose(user_id, session_id, agent_name, agent_type, mode, context)
      → Layer 1 (System) + Layer 2 (Workspace) + Layer 3 (Memory)

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
                "system_prompt": str,  # 完整的三层组合
                "agent_name": str,
                "agent_type": str,
                "mode": str,
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
```

**职责**: 协调三个 Layer 的加载顺序，组合为最终 prompt 字符串。

---

## 4. 调用流程与数据流

```
调用方 (Agent / ChatService)
  │
  │  invoke({user_id, session_id, context: {...}})
  ▼
PromptComposer
  │
  ├──► SystemPromptBuilder.load(agent_name)
  │     └── 读取 workspace/SYSTEM_PROMPT_{agent_name}.md
  │
  ├──► WorkspaceLoader.invoke({session_mode})  [LangChain Runnable]
  │     └── 读取 SOUL.md / IDENTITY.md / USER.md / AGENTS.md / TOOLS.md / BOOTSTRAP.md
  │     └── (仅 main) + MEMORY.md
  │
  └──► MemoryLoader.load(user_id, session_id, mode)
        └── 读取 memory/YYYY-MM-DD.md (今日 + 昨日)
        └── (仅 main) + MEMORY.md
  │
  ▼
组合输出: Layer 1 + Layer 2 + Layer 3
```

---

## 5. 错误处理

| 场景 | 处理方式 |
|------|---------|
| `SYSTEM_PROMPT_{agent}.md` 不存在 | 返回空字符串，不影响 Layer 2/3 |
| workspace 文件不存在 | 跳过该文件，继续加载其他的 |
| `memory/` 目录不存在 | 返回空字符串 |
| 每日 memory 文件不存在 | 返回空字符串（允许新建） |
| frontmatter 存在 | 自动剥离（`_strip_frontmatter` 函数） |
| 文件读取失败 | 记录警告日志，跳过该文件 |

---

## 6. 向后兼容

`app/graph/sys_prompt_builder.py` 保留作为兼容层：

```python
# 兼容现有调用方式
def get_supervisor_loader(mode="main"):
    composer = PromptComposer(
        agent_name="Supervisor",
        agent_type="Planning Coordinator",
        mode=mode,
    )
    # 返回可调用的 composer（LangChain Runnable）
    return composer
```

现有 Agent（`supervisor.py`、`chat_service.py`）无需修改接口，逐步迁移。

---

## 7. 新增文件清单

| 文件 | 描述 |
|------|------|
| `app/graph/prompt/__init__.py` | 导出 PromptComposer 及主要类 |
| `app/graph/prompt/config.py` | 路径配置、常量定义 |
| `app/graph/prompt/system_builder.py` | Layer 1 实现 |
| `app/graph/prompt/workspace_loader.py` | Layer 2 实现（LangChain Runnable） |
| `app/graph/prompt/memory_loader.py` | Layer 3 实现 |
| `app/graph/prompt/composer.py` | PromptComposer（LangChain Runnable） |

---

## 8. 待创建的系统提示词文件

| 文件 | 对应 Agent |
|------|-----------|
| `workspace/SYSTEM_PROMPT_supervisor.md` | Planning Agent |
| `workspace/SYSTEM_PROMPT_attractions.md` | Attractions Agent |
| `workspace/SYSTEM_PROMPT_budget.md` | Budget Agent |
| `workspace/SYSTEM_PROMPT_route.md` | Route Agent |
| `workspace/SYSTEM_PROMPT_food.md` | Food Agent |
| `workspace/SYSTEM_PROMPT_hotel.md` | Hotel Agent |
| `workspace/SYSTEM_PROMPT_preference.md` | Preference Agent |

每个文件定义该 Agent 的：角色定位、能力边界、安全规则、工具指令、格式约束、行为策略。
