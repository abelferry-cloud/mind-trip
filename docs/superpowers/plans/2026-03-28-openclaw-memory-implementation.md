# OpenClaw Memory Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate from SQLite-only memory to OpenClaw's Markdown-based "Markdown is Source of Truth" architecture. AI will write to MEMORY.md and daily logs; system reads at session start and injects into system prompt. Hybrid RAG via Ollama qwen3-embedding:0.6b + BM25.

**Architecture:**
- Phase 1: Create `MarkdownMemoryManager`, `DailyLogManager`, `MemoryInjector` + update workspace files + config
- Phase 2: Redirect `PreferenceAgent` writes from SQLite to Markdown
- Phase 3: Integrate `MemoryInjector` into chat service and supervisor agent
- Phase 4: Build `MemorySearchManager` with Ollama hybrid RAG
- Phase 5: Delete old SQLite/JSONL components
- Phase 6: Frontend Memory tab (optional, lower priority)

**Tech Stack:** Python asyncio, aiohttp (for Ollama), filelock, pydantic-settings, FastAPI, LangChain

---

## File Structure (Final State)

```
app/
├── memory/
│   ├── __init__.py              # Re-export new managers
│   ├── markdown_memory.py       # NEW: MarkdownMemoryManager
│   ├── daily_log.py            # NEW: DailyLogManager
│   ├── injector.py              # NEW: MemoryInjector
│   ├── search.py               # NEW: MemorySearchManager (Phase 4)
│   ├── short_term.py            # KEEP (in-memory only)
│   ├── long_term.py             # DELETE (Phase 5)
│   ├── session_persistence.py   # DELETE (Phase 5)
│   ├── session_manager.py        # SIMPLIFY (Phase 5)
│   ├── daily_writer.py          # DELETE (replaced by daily_log.py)
│   ├── sessions/                 # DELETE (Phase 5)
│   └── log/                      # DELETE (Phase 5, data moves to workspace/memory/)
├── workspace/
│   ├── memory/                  # NEW: Daily logs (was app/memory/log/)
│   ├── MEMORY.md                # UPDATE: Curated long-term memory template
│   ├── BOOTSTRAP.md             # UPDATE: Session init ceremony
│   └── TOOLS.md                 # UPDATE: Add memory tool descriptions
├── agents/
│   ├── preference.py            # MODIFY: Write to Markdown instead of SQLite
│   └── supervisor.py            # MODIFY: Use new preference flow
├── services/
│   └── chat_service.py          # MODIFY: Integrate MemoryInjector
├── graph/
│   └── sys_prompt_builder.py    # MODIFY: Accept injected memory
├── api/
│   └── session.py               # MODIFY: Markdown-based session list
├── config.py                    # MODIFY: Add memory/ollama settings
└── main.py                      # MODIFY: Remove SQLite lifespan
```

---

## Phase 1: Foundation

### Task 1: Update config.py with memory and Ollama settings

**Files:**
- Modify: `app/config.py:36-38`

- [ ] **Step 1: Add new settings to Settings class**

Run: Read `app/config.py` first to see the current class.

Add after `model_chain_list` property (around line 37):

```python
    # Memory
    memory_dir: str = "app/workspace/memory"
    memory_file: str = "app/workspace/MEMORY.md"

    # Ollama (for embedding)
    ollama_base_url: str = "http://localhost:11434"
    embedding_model: str = "qwen3-embedding:0.6b"

    # RAG settings
    rag_top_k: int = 5
    rag_bm25_k1: float = 1.5
    rag_bm25_b: float = 0.75
    rag_rrf_k: int = 60
    rag_temporal_decay_days: int = 30
```

- [ ] **Step 2: Commit**

```bash
git add app/config.py
git commit -m "feat(config): add memory and Ollama RAG settings"
```

---

### Task 2: Create DailyLogManager

**Files:**
- Create: `app/memory/daily_log.py`
- Create: `tests/memory/test_daily_log.py`

**Dependency:** Task 1 (config)

- [ ] **Step 1: Write failing test**

```python
# tests/memory/test_daily_log.py
import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from app.memory.daily_log import DailyLogManager

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)

@pytest.fixture
def manager(temp_dir):
    return DailyLogManager(memory_dir=temp_dir)

def test_append_creates_daily_file(manager, temp_dir):
    """Appending a message pair creates today's daily log file."""
    manager.append(
        session_id="sess_001",
        user_id="user_001",
        human_message="我想去成都",
        ai_message="成都3天行程已规划好",
    )
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = temp_dir / f"{today}.md"
    assert log_file.exists()
    content = log_file.read_text()
    assert "## Session: sess_001" in content
    assert "Human: 我想去成都" in content
    assert "AI: 成都3天行程已规划好" in content

def test_append_multiple_sessions_same_day(manager, temp_dir):
    """Multiple sessions append to the same daily file."""
    manager.append("sess_001", "u1", "msg1", "resp1")
    manager.append("sess_002", "u2", "msg2", "resp2")
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = temp_dir / f"{today}.md"
    content = log_file.read_text()
    assert "## Session: sess_001" in content
    assert "## Session: sess_002" in content

def test_read_today_and_yesterday_returns_empty_on_fresh_day(manager, temp_dir):
    """Fresh day returns today's empty header."""
    result = manager.read_today_and_yesterday()
    today = datetime.now().strftime("%Y-%m-%d")
    assert f"# {today}" in result

def test_read_session_across_days(manager, temp_dir):
    """A session spanning multiple days returns all entries."""
    # Manually create two day files with same session
    day1 = temp_dir / "2026-03-27.md"
    day1.write_text("# 2026-03-27\n\n## Session: sess_cross\n[20:00]\nHuman: msg1\nAI: resp1\n")
    day2 = temp_dir / "2026-03-28.md"
    day2.write_text("# 2026-03-28\n\n## Session: sess_cross\n[09:00]\nHuman: msg2\nAI: resp2\n")
    result = manager.read_session("sess_cross")
    assert "msg1" in result
    assert "msg2" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/memory/test_daily_log.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```python
# app/memory/daily_log.py
"""DailyLogManager - Append-only daily session logs at memory/YYYY-MM-DD.md

Reference: OpenClaw memory/YYYY-MM-DD.md daily session log format.
"""
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from filelock import FileLock


class DailyLogManager:
    """Append-only daily session logs.

    File format (per memory/YYYY-MM-DD.md):
        # 2026-03-28

        ## Session: abc123

        [20:45:33]
        Human: message
        AI: response

        ## Session: def456
        ...
    """

    def __init__(self, memory_dir: Optional[str] = None):
        if memory_dir is None:
            memory_dir = Path(__file__).parent.parent / "workspace" / "memory"
        else:
            memory_dir = Path(memory_dir)
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def _get_date_file(self, date: datetime) -> Path:
        return self.memory_dir / f"{date.strftime('%Y-%m-%d')}.md"

    def _ensure_date_header(self, fp, date: datetime) -> None:
        """Append date header to file if not already present."""
        date_str = date.strftime("%Y-%m-%d")
        fp.write(f"\n# {date_str}\n\n")

    def _session_block_exists(self, session_id: str, content: str) -> bool:
        return f"## Session: {session_id}" in content

    def _append_session_block(self, fp, session_id: str, user_id: str) -> None:
        """Append a new session block."""
        now = datetime.now()
        timestamp = now.strftime("%H:%M:%S")
        fp.write(f"## Session: {session_id}\n\n")
        fp.write(f"[{timestamp}]\n")
        fp.write(f"Human: [session start]\n")
        fp.write(f"AI: [ready]\n\n")

    def append(
        self,
        session_id: str,
        user_id: str,
        human_message: str,
        ai_message: str,
    ) -> None:
        """Append a human/AI message pair to today's daily log.

        Uses file locking for concurrent safety.
        Creates session block if first message from this session today.
        """
        now = datetime.now()
        date_file = self._get_date_file(now)
        lock_file = date_file.with_suffix(".lock")

        lock = FileLock(str(lock_file), timeout=10)
        with lock:
            existing = date_file.read_text(encoding="utf-8") if date_file.exists() else ""

            lines = []
            if not existing.strip():
                self._ensure_date_header(lines.append if hasattr(lines, 'append') else None, now)
                lines_to_write = f"# {now.strftime('%Y-%m-%d')}\n\n"
            else:
                lines_to_write = ""

            if not self._session_block_exists(session_id, existing):
                lines_to_write += f"## Session: {session_id}\n\n"

            timestamp = now.strftime("%H:%M:%S")
            lines_to_write += f"[{timestamp}]\n"
            lines_to_write += f"Human: {human_message}\n"
            lines_to_write += f"AI: {ai_message}\n\n"

            mode = "a" if date_file.exists() else "w"
            with open(date_file, mode, encoding="utf-8") as f:
                if mode == "w":
                    f.write(f"# {now.strftime('%Y-%m-%d')}\n\n")
                if not self._session_block_exists(session_id, existing if date_file.exists() else ""):
                    f.write(f"## Session: {session_id}\n\n")
                f.write(f"[{timestamp}]\n")
                f.write(f"Human: {human_message}\n")
                f.write(f"AI: {ai_message}\n\n")

    def read_today_and_yesterday(self) -> str:
        """Read today's and yesterday's daily logs concatenated."""
        now = datetime.now()
        yesterday = now - timedelta(days=1)

        result = ""
        for d in [yesterday, now]:
            f = self._get_date_file(d)
            if f.exists():
                result += f.read_text(encoding="utf-8") + "\n"
            else:
                result += f"# {d.strftime('%Y-%m-%d')}\n\n"
        return result

    def read_session(self, session_id: str) -> str:
        """Read all entries for a specific session across daily logs.

        Scans all memory/*.md files in date order (oldest first).
        Returns empty string if session not found.
        """
        if not self.memory_dir.exists():
            return ""

        session_blocks = []
        for f in sorted(self.memory_dir.glob("*.md")):
            content = f.read_text(encoding="utf-8")
            # Find all session blocks
            pattern = rf"(## Session: {re.escape(session_id)}.*?)(?=\n## Session: |\n---|\Z)"
            for match in re.finditer(pattern, content, re.DOTALL):
                block = match.group(1).strip()
                if block:
                    session_blocks.append(block)

        return "\n\n".join(session_blocks)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/memory/test_daily_log.py -v`
Expected: PASS (may need minor adjustments to implementation)

- [ ] **Step 5: Commit**

```bash
git add app/memory/daily_log.py tests/memory/test_daily_log.py
git commit -m "feat(memory): add DailyLogManager for append-only daily session logs"
```

---

### Task 3: Create MarkdownMemoryManager

**Files:**
- Create: `app/memory/markdown_memory.py`
- Create: `tests/memory/test_markdown_memory.py`

- [ ] **Step 1: Write failing test**

```python
# tests/memory/test_markdown_memory.py
import pytest
import tempfile
from pathlib import Path
from app.memory.markdown_memory import MarkdownMemoryManager, MEMORY_TEMPLATE

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)

def test_get_memory_returns_empty_when_file_missing(temp_dir):
    """Missing MEMORY.md returns empty string."""
    mgr = MarkdownMemoryManager(memory_path=temp_dir / "MEMORY.md")
    result = mgr.get_memory()
    assert result == ""

def test_get_memory_returns_content_when_file_exists(temp_dir):
    """Existing MEMORY.md returns its content."""
    mem_file = temp_dir / "MEMORY.md"
    mem_file.write_text("# MEMORY.md\n\n## User Profile\n\n- **Name**: 张三")
    mgr = MarkdownMemoryManager(memory_path=mem_file)
    result = mgr.get_memory()
    assert "张三" in result

def test_update_preference_creates_file_if_missing(temp_dir):
    """update_preference creates MEMORY.md from template if missing."""
    mgr = MarkdownMemoryManager(memory_path=temp_dir / "MEMORY.md")
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        mgr.update_preference("user_001", "spending_style", "节省")
    )
    mem_file = temp_dir / "MEMORY.md"
    assert mem_file.exists()
    content = mem_file.read_text()
    assert "节省" in content

def test_update_preference_appends_to_existing_file(temp_dir):
    """update_preference appends new preference to existing MEMORY.md."""
    mem_file = temp_dir / "MEMORY.md"
    mem_file.write_text("# MEMORY.md\n\n## Travel Preferences\n\n- **Hardships to avoid**: 硬座\n")
    mgr = MarkdownMemoryManager(memory_path=mem_file)
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        mgr.update_preference("user_001", "health", "心脏病")
    )
    content = mem_file.read_text()
    assert "硬座" in content
    assert "心脏病" in content

def test_update_user_profile_replaces_profile_section(temp_dir):
    """update_user_profile replaces existing User Profile section."""
    mem_file = temp_dir / "MEMORY.md"
    mem_file.write_text("# MEMORY.md\n\n## User Profile\n\n- **Name**: 李四\n")
    mgr = MarkdownMemoryManager(memory_path=mem_file)
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        mgr.update_user_profile("user_001", {
            "name": "王五",
            "preferred_name": "小王",
            "timezone": "Asia/Shanghai",
        })
    )
    content = mem_file.read_text()
    assert "王五" in content
    assert "小王" in content
    assert "李四" not in content  # old name replaced
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/memory/test_markdown_memory.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```python
# app/memory/markdown_memory.py
"""MarkdownMemoryManager - Manages MEMORY.md as the curated long-term memory file.

Reference: OpenClaw's "Markdown is Source of Truth" — files are the single source
of truth, not a database. The model only "remembers" what gets written to disk.
"""
import re
from pathlib import Path
from typing import Any, Dict, Optional

MEMORY_TEMPLATE = """# MEMORY.md - Long-term Memory

_Last updated: {date}_

## User Profile

- **Name**: [user's name]
- **Preferred Name**: [what they like to be called]
- **Timezone**: Asia/Shanghai
- **Spending Style**: [节省/适中/奢侈]
- **Travel Style**: [结构化计划/灵活随性]

## Health Notes

- [any health conditions to be aware of]

## Travel Preferences

- **Preferred transport**: [地铁/公交/出租车/步行]
- **Hardships to avoid**: [硬座/红眼航班/转机/爬山]
- **City preferences**: [previously visited cities]

## Key Decisions

- [important planning decisions from past sessions]

---

_Last updated by AI after session_
"""


class MarkdownMemoryManager:
    """Manages MEMORY.md - the curated long-term memory file.

    Implements atomic writes using rename-to-write pattern:
    1. Write to temp file
    2. Rename temp to target (atomic on POSIX)
    """

    def __init__(self, memory_path: Optional[str] = None):
        if memory_path is None:
            memory_path = Path(__file__).parent.parent / "workspace" / "MEMORY.md"
        else:
            memory_path = Path(memory_path)
        self.memory_path = memory_path

    def _ensure_file_exists(self) -> None:
        """Create MEMORY.md from template if it doesn't exist."""
        if not self.memory_path.exists():
            from datetime import datetime
            content = MEMORY_TEMPLATE.format(date=datetime.now().strftime("%Y-%m-%d"))
            self.memory_path.parent.mkdir(parents=True, exist_ok=True)
            self.memory_path.write_text(content, encoding="utf-8")

    def get_memory(self) -> str:
        """Read and return MEMORY.md content.

        Returns empty string if file doesn't exist.
        """
        if not self.memory_path.exists():
            return ""
        return self.memory_path.read_text(encoding="utf-8")

    async def update_user_profile(self, user_id: str, profile: Dict[str, Any]) -> None:
        """Update the User Profile section in MEMORY.md.

        Replaces existing User Profile section with updated values.
        Preserves all other sections.
        """
        self._ensure_file_exists()
        content = self.memory_path.read_text(encoding="utf-8")

        # Build new profile section
        from datetime import datetime
        new_profile = f"""## User Profile

- **Name**: {profile.get('name', '[user\'s name]')}
- **Preferred Name**: {profile.get('preferred_name', '[what they like to be called]')}
- **Timezone**: {profile.get('timezone', 'Asia/Shanghai')}
- **Spending Style**: {profile.get('spending_style', '[节省/适中/奢侈]')}
- **Travel Style**: {profile.get('travel_style', '[结构化计划/灵活随性]')}

"""
        # Replace existing User Profile section
        pattern = r"(## User Profile\n\n- \*\*Name\*\*:.*?\n)(?=\n## |\Z)"
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, new_profile, content, count=1, flags=re.DOTALL)
        else:
            # Insert before "## Health Notes"
            content = content.replace("## Health Notes", new_profile + "## Health Notes", 1)

        # Update last updated date
        content = re.sub(
            r"_Last updated: .*?_",
            f"_Last updated: {datetime.now().strftime('%Y-%m-%d')}_",
            content,
        )

        self._atomic_write(content)

    async def update_preference(self, user_id: str, category: str, value: Any) -> None:
        """Update a specific preference category in MEMORY.md.

        Categories:
        - spending_style: str (节省/适中/奢侈)
        - health: list (health conditions)
        - hardships: list (hardhips to avoid)
        - city_preferences: list (previously visited cities)
        - transport: str (preferred transport)
        """
        self._ensure_file_exists()
        content = self.memory_path.read_text(encoding="utf-8")

        # Map category to section and formatting
        category_map = {
            "spending_style": ("Spending Style", lambda v: f"- **Spending Style**: {v}"),
            "health": ("Health Notes", lambda v: f"- {v}" if isinstance(v, str) else f"- {', '.join(v)}"),
            "hardships": ("Hardships to avoid", lambda v: f"- {v}" if isinstance(v, str) else f"- {', '.join(v)}"),
            "city_preferences": ("City preferences", lambda v: f"- {v}" if isinstance(v, str) else f"- {', '.join(v)}"),
            "transport": ("Preferred transport", lambda v: f"- **Preferred transport**: {v}"),
        }

        if category not in category_map:
            return

        section_name, formatter = category_map[category]
        new_line = formatter(value)

        # Check if this category already exists in its section
        section_pattern = rf"(## {section_name}\n\n)(- .*?\n)*"
        if re.search(section_pattern, content):
            # Update existing entry in section
            entry_pattern = rf"(- {re.escape(str(value))}|- \*\*{re.escape(category.replace('_', ' '))}\*\*:.*?)\n"
            if not re.search(entry_pattern, content):
                content = re.sub(
                    section_pattern,
                    lambda m: m.group(0) + f"- {value}\n",
                    content,
                    count=1,
                )
        else:
            # Insert new section entry before "## Key Decisions"
            insert_before = "## Key Decisions"
            if insert_before in content:
                content = content.replace(
                    insert_before,
                    f"## {section_name}\n\n{new_line}\n\n{insert_before}",
                    1,
                )
            else:
                content += f"\n## {section_name}\n\n{new_line}\n"

        from datetime import datetime
        content = re.sub(
            r"_Last updated: .*?_",
            f"_Last updated: {datetime.now().strftime('%Y-%m-%d')}_",
            content,
        )

        self._atomic_write(content)

    async def append_decision(self, session_id: str, decision: str) -> None:
        """Append a key decision under '## Key Decisions' section."""
        self._ensure_file_exists()
        content = self.memory_path.read_text(encoding="utf-8")

        # Append to Key Decisions section
        key_decisions_marker = "## Key Decisions"
        if key_decisions_marker in content:
            # Find the section and append
            pattern = r"(## Key Decisions\n\n)(- .*?\n)*"
            repl = rf"\1\2- {decision}\n"
            content = re.sub(pattern, repl, content, count=1)
        else:
            # Create section before the final separator
            content = content.replace("\n---", f"\n## Key Decisions\n\n- {decision}\n\n---", 1)

        from datetime import datetime
        content = re.sub(
            r"_Last updated: .*?_",
            f"_Last updated: {datetime.now().strftime('%Y-%m-%d')}_",
            content,
        )

        self._atomic_write(content)

    def _atomic_write(self, content: str) -> None:
        """Atomic write: write to temp file, then rename to target."""
        temp_file = self.memory_path.with_suffix(".md.tmp")
        temp_file.write_text(content, encoding="utf-8")
        temp_file.replace(self.memory_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/memory/test_markdown_memory.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/memory/markdown_memory.py tests/memory/test_markdown_memory.py
git commit -m "feat(memory): add MarkdownMemoryManager for MEMORY.md read/write"
```

---

### Task 4: Create MemoryInjector

**Files:**
- Create: `app/memory/injector.py`
- Create: `tests/memory/test_injector.py`

**Dependency:** Task 2 (DailyLogManager), Task 3 (MarkdownMemoryManager)

- [ ] **Step 1: Write failing test**

```python
# tests/memory/test_injector.py
import pytest
import tempfile
from pathlib import Path
from app.memory.injector import MemoryInjector
from app.memory.markdown_memory import MarkdownMemoryManager
from app.memory.daily_log import DailyLogManager

@pytest.fixture
def temp_workspace(tmp_path):
    mem_dir = tmp_path / "memory"
    mem_dir.mkdir()
    mem_file = tmp_path / "MEMORY.md"
    return {"mem_dir": mem_dir, "mem_file": mem_file}

def test_load_session_memory_main_mode_includes_memory_and_daily(temp_workspace):
    """mode=main loads MEMORY.md + today + yesterday."""
    mem_mgr = MarkdownMemoryManager(memory_path=temp_workspace["mem_file"])
    dl_mgr = DailyLogManager(memory_dir=temp_workspace["mem_dir"])
    inj = MemoryInjector(mem_mgr, dl_mgr)

    # Write something to MEMORY.md
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        mem_mgr.update_preference("user_001", "spending_style", "节省")
    )

    # Write something to daily log
    dl_mgr.append("sess_001", "user_001", "hello", "hi")

    result = asyncio.get_event_loop().run_until_complete(
        inj.load_session_memory("user_001", "sess_001", mode="main")
    )
    assert "节省" in result
    assert "hello" in result

def test_load_session_memory_shared_mode_skips_memory(temp_workspace):
    """mode=shared skips MEMORY.md, only loads daily logs."""
    mem_mgr = MarkdownMemoryManager(memory_path=temp_workspace["mem_file"])
    dl_mgr = DailyLogManager(memory_dir=temp_workspace["mem_dir"])
    inj = MemoryInjector(mem_mgr, dl_mgr)

    import asyncio
    asyncio.get_event_loop().run_until_complete(
        mem_mgr.update_preference("user_001", "spending_style", "节省")
    )
    dl_mgr.append("sess_001", "user_001", "hello", "hi")

    result = asyncio.get_event_loop().run_until_complete(
        inj.load_session_memory("user_001", "sess_001", mode="shared")
    )
    assert "节省" not in result  # MEMORY.md skipped
    assert "hello" in result     # daily log included
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/memory/test_injector.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```python
# app/memory/injector.py
"""MemoryInjector - Composes memory content into system prompt at session start.

Reference: OpenClaw session start memory loading:
- memory/YYYY-MM-DD.md (today + yesterday) always loaded
- MEMORY.md loaded only in main (private) session mode
"""
from typing import Literal, Optional

from app.memory.markdown_memory import MarkdownMemoryManager
from app.memory.daily_log import DailyLogManager


class MemoryInjector:
    """Composes memory content for injection into system prompt at session start.

    Memory loaded per session mode:
    - "main":   MEMORY.md + today + yesterday daily logs
    - "shared": today + yesterday daily logs only
    """

    def __init__(
        self,
        memory_manager: Optional[MarkdownMemoryManager] = None,
        daily_log_manager: Optional[DailyLogManager] = None,
    ):
        if memory_manager is None:
            memory_manager = MarkdownMemoryManager()
        if daily_log_manager is None:
            daily_log_manager = DailyLogManager()
        self.memory_manager = memory_manager
        self.daily_log_manager = daily_log_manager

    async def load_session_memory(
        self,
        user_id: str,
        session_id: str,
        mode: Literal["main", "shared"] = "main",
        query: Optional[str] = None,
    ) -> str:
        """Load all relevant memory for a session and compose as markdown string.

        Args:
            user_id: user identifier
            session_id: current session identifier
            mode: "main" (includes MEMORY.md) or "shared" (daily logs only)
            query: optional search query for RAG retrieval (Phase 4)

        Returns:
            Markdown string to inject into system prompt under '## Memory' section.
        """
        parts = []

        # Daily logs (today + yesterday) — always loaded
        daily_content = self.daily_log_manager.read_today_and_yesterday()
        if daily_content:
            parts.append(f"## 今日与昨日会话日志\n\n{daily_content}")

        # Long-term memory — only in main private session
        if mode == "main":
            memory_content = self.memory_manager.get_memory()
            if memory_content:
                parts.append(f"## 长期记忆 (MEMORY.md)\n\n{memory_content}")

        return "\n\n".join(parts) if parts else ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/memory/test_injector.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/memory/injector.py tests/memory/test_injector.py
git commit -m "feat(memory): add MemoryInjector for session start memory composition"
```

---

### Task 5: Update workspace files

**Files:**
- Modify: `app/workspace/MEMORY.md` (replace with template)
- Modify: `app/workspace/BOOTSTRAP.md` (update ceremony)
- Modify: `app/workspace/TOOLS.md` (add memory tool descriptions)

**Dependency:** Tasks 2, 3, 4

- [ ] **Step 1: Replace MEMORY.md with template**

Run: Read current `app/workspace/MEMORY.md` (it's likely empty/1 line).

Replace content with the MEMORY_TEMPLATE from Task 3 (without the Python variable syntax):

```markdown
# MEMORY.md - Long-term Memory

_Last updated: 2026-03-28_

## User Profile

- **Name**: [user's name]
- **Preferred Name**: [what they like to be called]
- **Timezone**: Asia/Shanghai
- **Spending Style**: [节省/适中/奢侈]
- **Travel Style**: [结构化计划/灵活随性]

## Health Notes

- [any health conditions to be aware of]

## Travel Preferences

- **Preferred transport**: [地铁/公交/出租车/步行]
- **Hardships to avoid**: [硬座/红眼航班/转机/爬山]
- **City preferences**: [previously visited cities]

## Key Decisions

- [important planning decisions from past sessions]

---

_Last updated by AI after session_
```

- [ ] **Step 2: Update BOOTSTRAP.md**

Run: Read current `app/workspace/BOOTSTRAP.md`.

Replace with the updated ceremony that reflects the memory architecture:

```markdown
# BOOTSTRAP.md - Session Initialization Ceremony

## On First Run

1. Check if MEMORY.md exists → if not, create from template
2. Check if memory/ directory exists → if not, create
3. Initialize empty today's log if not exists

## On Every Session Start

1. MemoryInjector loads today's + yesterday's daily logs
2. If mode="main", also load MEMORY.md
3. Compose into system prompt under "## Memory" section

## On Every Message

1. Save to daily log (append-only)
2. If preference mentioned → update MEMORY.md
```

- [ ] **Step 3: Add memory tools to TOOLS.md**

Run: Read `app/workspace/TOOLS.md`.

Add before the final section (or at the end):

```markdown
## Memory Tools

### write_memory
Write important information to long-term memory (MEMORY.md).
Parameters: content (string) - what to remember

### append_daily_log
Append entry to today's session log.
Parameters: session_id, human_message, ai_message

### search_memory
Search across all memory files using semantic similarity.
Parameters: query (string), top_k (int, default 5)
Returns: Relevant memory chunks with scores
```

- [ ] **Step 4: Create memory directory and initial daily log**

```bash
mkdir -p app/workspace/memory
touch app/workspace/memory/.gitkeep
```

- [ ] **Step 5: Commit**

```bash
git add app/workspace/MEMORY.md app/workspace/BOOTSTRAP.md app/workspace/TOOLS.md
git commit -m "feat(workspace): update BOOTSTRAP.md and TOOLS.md for memory architecture"
```

---

## Phase 2: Redirect Writes

### Task 6: Rewrite PreferenceAgent to write Markdown

**Files:**
- Modify: `app/agents/preference.py`
- Create: `tests/agents/test_preference.py`

**Dependency:** Tasks 3, 4, 5

- [ ] **Step 1: Write failing test**

```python
# tests/agents/test_preference.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.agents.preference import PreferenceAgent

@pytest.mark.asyncio
async def test_parse_and_update_health_keywords():
    """Health keywords in message trigger health preference update."""
    with patch('app.agents.preference.get_markdown_memory_manager') as mock_get:
        mock_mgr = MagicMock()
        mock_mgr.update_preference = AsyncMock()
        mock_get.return_value = mock_mgr

        agent = PreferenceAgent()
        result = await agent.parse_and_update("user_001", "我有心脏病和糖尿病")

        # Should have triggered 2 health updates
        calls = mock_mgr.update_preference.call_args_list
        categories = [call[0][1] for call in calls]  # [1] is category
        assert "health" in categories
        assert result["updated"]  # non-empty
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_preference.py -v`
Expected: FAIL — PreferenceAgent still using SQLite

- [ ] **Step 3: Rewrite PreferenceAgent**

Read `app/agents/preference.py` and rewrite to use MarkdownMemoryManager instead of SQLite:

```python
# app/agents/preference.py
"""偏好 Agent - 管理长期记忆中的用户偏好 (Markdown 版本).

这是唯一可以写入长期记忆的 Agent。
写入目标：MEMORY.md（长期）+ memory/YYYY-MM-DD.md（每日）
"""
from typing import Any, Dict
from app.memory.markdown_memory import MarkdownMemoryManager, get_markdown_memory_manager
from app.memory.daily_log import DailyLogManager, get_daily_log_manager


class PreferenceAgent:
    """负责读写用户偏好的 Agent (Markdown 版本).

    该 Agent 是唯一可以写入长期 Markdown 记忆的 Agent。
    其他 Agent 调用 get_preference() 读取但不能写入。
    """

    def __init__(self):
        self._memory_mgr: MarkdownMemoryManager = get_markdown_memory_manager()
        self._daily_mgr: DailyLogManager = get_daily_log_manager()

    async def update_preference(self, user_id: str, category: str, value: Any) -> Dict[str, bool]:
        """更新用户的单个偏好类别到 MEMORY.md。"""
        await self._memory_mgr.update_preference(user_id, category, value)
        return {"success": True}

    async def get_preference(self, user_id: str) -> Dict[str, Any]:
        """获取用户的所有偏好（从 MEMORY.md 读取）。

        Returns:
            偏好字典，按 category 组织。
        """
        content = self._memory_mgr.get_memory()
        # Parse MEMORY.md for preferences
        prefs = {}
        import re
        # spending_style
        m = re.search(r"- \*\*Spending Style\*\*: (.+?)\n", content)
        if m:
            prefs["spending_style"] = m.group(1).strip()
        # health
        health_section = re.search(r"## Health Notes\n\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
        if health_section:
            health_items = re.findall(r"- (.+?)\n", health_section.group(1))
            prefs["health"] = health_items
        # hardships
        hardships_section = re.search(r"## Travel Preferences\n\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
        if hardships_section:
            prefs["hardships"] = []
        return prefs

    async def parse_and_update(self, user_id: str, message: str) -> Dict[str, Any]:
        """解析用户消息中的偏好提示并更新记忆。

        查找如下模式：
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


# Singleton factory
_memory_mgr_instance: MarkdownMemoryManager | None = None
_daily_mgr_instance: DailyLogManager | None = None


def get_markdown_memory_manager() -> MarkdownMemoryManager:
    global _memory_mgr_instance
    if _memory_mgr_instance is None:
        _memory_mgr_instance = MarkdownMemoryManager()
    return _memory_mgr_instance


def get_daily_log_manager() -> DailyLogManager:
    global _daily_mgr_instance
    if _daily_mgr_instance is None:
        _daily_mgr_instance = DailyLogManager()
    return _daily_mgr_instance
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agents/test_preference.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/preference.py tests/agents/test_preference.py
git commit -m "feat(agent): redirect PreferenceAgent writes to Markdown instead of SQLite"
```

---

### Task 7: Update SupervisorAgent to use new preference flow

**Files:**
- Modify: `app/agents/supervisor.py:76-85` (init)
- Modify: `app/agents/supervisor.py:117-120` (parse_and_update call)

**Dependency:** Task 6

- [ ] **Step 1: Review current supervisor preference calls**

Run: `grep -n "preference\|PreferenceAgent\|get_preference\|parse_and_update" app/agents/supervisor.py`

The current code at line 118-120 does:
```python
pref_result = await trace("Preference Agent",
    self.pref_agent.parse_and_update(user_id, message))
preferences = await self.pref_agent.get_preference(user_id)
```

The `get_preference` now reads from MEMORY.md. The `parse_and_update` writes to MEMORY.md.

- [ ] **Step 2: No code changes needed**

The existing calls in supervisor.py already call `parse_and_update` and `get_preference`. After Task 6, these will automatically work with Markdown.

However, we need to ensure `PreferenceAgent` is instantiated with the new constructor (no db_path needed).

- [ ] **Step 3: Commit**

```bash
git add app/agents/supervisor.py
git commit -m "chore(supervisor): no changes needed - already calls parse_and_update/get_preference"
```

---

### Task 8: Update session API to use Markdown-based session list

**Files:**
- Modify: `app/api/session.py`

**Dependency:** Tasks 2, 5

- [ ] **Step 1: Review current session API**

Run: `cat app/api/session.py`

Current `GET /api/sessions` uses `SessionMemoryManager` backed by JSONL. We need to scan `memory/*.md` files instead.

- [ ] **Step 2: Rewrite session API to scan daily log files**

```python
# app/api/session.py (rewrite)
"""会话管理 API - 基于 Markdown daily logs 的会话接口。

Reference: OpenClaw's memory/YYYY-MM-DD.md session tracking.
Session list derived from scanning memory/ files for ## Session: blocks.
"""
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

from app.memory.daily_log import DailyLogManager, get_daily_log_manager

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class CreateSessionResponse(BaseModel):
    session_id: str


class DeleteSessionResponse(BaseModel):
    success: bool
    message: str


class MessageItem(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    id: str | None = None
    timestamp: str | None = None


class SessionMessagesResponse(BaseModel):
    session_id: str
    messages: List[MessageItem]


class SessionInfo(BaseModel):
    session_id: str
    history_count: int
    has_memory: bool


_daily_mgr: DailyLogManager = get_daily_log_manager()


def _scan_sessions_from_daily_logs() -> List[SessionInfo]:
    """Scan all memory/*.md files and extract unique sessions."""
    sessions = {}
    memory_dir = Path(__file__).parent.parent / "workspace" / "memory"
    if not memory_dir.exists():
        return []

    import re
    for f in sorted(memory_dir.glob("*.md")):
        if f.name.startswith("."):
            continue
        content = f.read_text(encoding="utf-8")
        # Find all ## Session: {id} blocks
        for match in re.finditer(r"## Session: (\S+)(?:\s+\[DELETED\])?", content):
            session_id = match.group(1)
            if session_id not in sessions:
                sessions[session_id] = {"id": session_id, "count": 0}
            sessions[session_id]["count"] += content.count(f"Human:", match.start())

    return [
        SessionInfo(
            session_id=s["id"],
            history_count=s["count"],
            has_memory=s["count"] > 0,
        )
        for s in sessions.values()
    ]


@router.post("", response_model=CreateSessionResponse)
async def create_session():
    """创建新会话（不写入文件，会话在首次消息时创建日志条目）。"""
    session_id = str(uuid.uuid4())
    return CreateSessionResponse(session_id=session_id)


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    """获取会话信息。"""
    sessions = _scan_sessions_from_daily_logs()
    for s in sessions:
        if s.session_id == session_id:
            return s
    # Return empty info for new session
    return SessionInfo(session_id=session_id, history_count=0, has_memory=False)


@router.get("/{session_id}/messages", response_model=SessionMessagesResponse)
async def get_session_messages(session_id: str):
    """获取会话的所有历史消息。"""
    session_content = _daily_mgr.read_session(session_id)
    if not session_content:
        return SessionMessagesResponse(session_id=session_id, messages=[])

    messages = []
    import re
    # Parse each [HH:MM:SS] Human: / AI: block
    pattern = r"\[(\d{2}:\d{2}:\d{2})\]\nHuman: (.+?)\nAI: (.+?)(?=\n\[|\Z)"
    for i, match in enumerate(re.finditer(pattern, session_content, re.DOTALL)):
        ts = match.group(1)
        messages.append(MessageItem(role="user", content=match.group(2).strip(), id=str(i * 2), timestamp=ts))
        messages.append(MessageItem(role="assistant", content=match.group(3).strip(), id=str(i * 2 + 1), timestamp=ts))

    return SessionMessagesResponse(session_id=session_id, messages=messages)


@router.get("", response_model=List[SessionInfo])
async def list_sessions():
    """列出所有会话。"""
    return _scan_sessions_from_daily_logs()


@router.delete("/{session_id}", response_model=DeleteSessionResponse)
async def delete_session(session_id: str):
    """删除会话（软删除：标记为 deleted）。"""
    # Append deletion marker to today's daily log
    from datetime import datetime
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    marker = f"\n## Session: {session_id} [DELETED]\n"
    memory_dir = Path(__file__).parent.parent / "workspace" / "memory"
    day_file = memory_dir / f"{date_str}.md"
    if day_file.exists():
        with open(day_file, "a", encoding="utf-8") as f:
            f.write(marker)

    # Update .deleted index
    deleted_index = memory_dir / ".deleted"
    import json
    deleted_data = {}
    if deleted_index.exists():
        deleted_data = json.loads(deleted_index.read_text(encoding="utf-8"))
    if "deleted_sessions" not in deleted_data:
        deleted_data["deleted_sessions"] = []
        deleted_data["deleted_at"] = {}
    if session_id not in deleted_data["deleted_sessions"]:
        deleted_data["deleted_sessions"].append(session_id)
        deleted_data["deleted_at"][session_id] = datetime.now(timezone.utc).isoformat()
    deleted_index.write_text(json.dumps(deleted_data, ensure_ascii=False, indent=2), encoding="utf-8")

    return DeleteSessionResponse(success=True, message=f"Session {session_id} 已标记为已删除")
```

- [ ] **Step 3: Commit**

```bash
git add app/api/session.py
git commit -m "feat(api): rewrite session API to scan Markdown daily logs instead of JSONL"
```

---

## Phase 3: Integrate Reads

### Task 9: Integrate MemoryInjector into ChatService

**Files:**
- Modify: `app/services/chat_service.py`
- Create: `tests/services/test_chat_service_memory.py`

**Dependency:** Tasks 4, 6, 7, 8

- [ ] **Step 1: Read current chat_service.py**

```python
# Current flow at line 37-109:
# 1. WorkspacePromptLoader.invoke() → system_prompt
# 2. get_memory(session_id).get_history() → formatted_history
# 3. full_system = system_prompt + history
# 4. router.call(prompt=message, system=full_system)
# 5. save_context + daily_writer.append + persistence.save_message
```

- [ ] **Step 2: Add MemoryInjector to ChatService**

Modify `app/services/chat_service.py`:

Add to imports (after existing imports):
```python
from app.memory.injector import MemoryInjector, get_memory_injector
```

In `__init__`, add:
```python
self._injector = get_memory_injector()
```

In `chat()` method, after line 54 (`system_prompt = prompt_result["system_prompt"]`):

```python
# 2. Load session memory (today + yesterday + MEMORY.md)
session_memory = await self._injector.load_session_memory(
    user_id=user_id,
    session_id=session_id,
    mode="main",
)
```

Then after `full_system = system_prompt` (line 67), add memory:
```python
if session_memory:
    full_system = f"{system_prompt}\n\n## Memory\n\n{session_memory}"
else:
    full_system = system_prompt
```

Also update the daily_writer to use the new DailyLogManager (the existing `daily_writer.py` uses `app/memory/log/` — we need to change it to `app/workspace/memory/`). Actually, since `DailyLogManager` defaults to `app/workspace/memory/`, this should just work.

But we need to update `chat_service.py` to remove the old `DailyMemoryWriter` import and replace with `DailyLogManager`:

Replace:
```python
from app.memory.daily_writer import DailyMemoryWriter
```
With:
```python
from app.memory.daily_log import DailyLogManager, get_daily_log_manager
```

And in `__init__`:
```python
self._daily_writer = get_daily_log_manager()  # replaces DailyMemoryWriter
```

And in `chat()` method, replace the `append` call:
Old:
```python
self._daily_writer.append(
    session_id=session_id,
    user_id=user_id,
    human_message=message,
    ai_message=answer,
)
```
New (same signature — it works):
```python
self._daily_writer.append(
    session_id=session_id,
    user_id=user_id,
    human_message=message,
    ai_message=answer,
)
```

Also remove `from app.memory.session_persistence import get_session_persistence` and the `self._persistence = get_session_persistence()` line — we'll remove JSONL persistence in Phase 5.

- [ ] **Step 3: Commit**

```bash
git add app/services/chat_service.py
git commit -m "feat(chat): integrate MemoryInjector and DailyLogManager into ChatService"
```

---

### Task 10: Update sys_prompt_builder to accept injected memory

**Files:**
- Modify: `app/graph/sys_prompt_builder.py`

**Dependency:** Task 9

- [ ] **Step 1: Check if sys_prompt_builder.py needs changes**

The current `WorkspacePromptLoader.invoke()` already returns a dict including `dynamic_context`. The injected memory from `MemoryInjector` is added in `chat_service.py` before calling `router.call()`.

The `sys_prompt_builder.py` itself doesn't need to change — it provides the raw workspace text, and `chat_service.py` composes it with memory.

However, for cleanliness, we should add a dedicated "Memory" section injection point in `WorkspacePromptLoader`.

- [ ] **Step 2: Add memory injection support to WorkspacePromptLoader**

Add to `WorkspacePromptLoader.__init__`:
```python
self.include_memory = include_memory  # bool
```

Add a new factory function:
```python
def get_supervisor_loader(..., include_memory: bool = True) -> WorkspacePromptLoader:
```

Actually, since the memory is injected in `chat_service.py` directly into `full_system`, no changes needed here. Skip this task.

---

### Task 11: Update SupervisorAgent plan() to trigger memory load

**Files:**
- Modify: `app/agents/supervisor.py:87-120` (the plan method)

**Dependency:** Tasks 6, 9

- [ ] **Step 1: Review if supervisor needs changes**

The `SupervisorAgent.plan()` doesn't directly call `MemoryInjector` — it goes through `ChatService`. However, the `plan()` method does its own preference reading via `PreferenceAgent.get_preference()`.

Currently at line 120:
```python
preferences = await self.pref_agent.get_preference(user_id)
```

After Task 6, this reads from MEMORY.md. No code changes needed — it should just work.

- [ ] **Step 2: Commit (no changes)**

```bash
git commit --allow-empty -m "chore(supervisor): plan() works with new PreferenceAgent after Task 6"
```

---

## Phase 4: RAG Search

### Task 12: Create MemorySearchManager with Ollama hybrid RAG

**Files:**
- Create: `app/memory/search.py`
- Create: `tests/memory/test_search.py`

**Dependency:** Tasks 1, 2, 5

- [ ] **Step 1: Write failing test**

```python
# tests/memory/test_search.py
import pytest
import tempfile
from pathlib import Path
from app.memory.search import MemorySearchManager, SearchResult

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)

@pytest.fixture
def search_mgr(temp_dir):
    return MemorySearchManager(memory_dir=temp_dir)

def test_bm25_score_returns_zero_for_no_match(search_mgr):
    """BM25 returns 0 when no query terms match."""
    score = search_mgr._bm25_score("心脏病 糖尿病", "我想去成都旅游")
    assert score == 0.0

def test_bm25_score_returns_positive_for_match(search_mgr):
    """BM25 returns positive score when query terms match."""
    score = search_mgr._bm25_score("成都 旅游", "成都三天旅游攻略")
    assert score > 0

def test_vector_score_returns_zero_for_empty_vectors(search_mgr):
    """Vector score with empty vectors returns 0."""
    score = search_mgr._vector_score([], [])
    assert score == 0.0

def test_vector_score_returns_one_for_identical_vectors(search_mgr):
    """Identical vectors return cosine similarity of 1."""
    score = search_mgr._vector_score([1.0, 0.0], [1.0, 0.0])
    assert abs(score - 1.0) < 0.001

def test_rrf_fusion_combines_rankings(search_mgr):
    """RRF fusion produces different rankings from either input alone."""
    r1 = [SearchResult(chunk="a", score=1.0, doc_path="f1"), SearchResult(chunk="b", score=0.5, doc_path="f2")]
    r2 = [SearchResult(chunk="b", score=1.0, doc_path="f2"), SearchResult(chunk="c", score=0.5, doc_path="f3")]
    fused = search_mgr._rrf_fusion([r1, r2], k=60)
    # b should rank high (in both lists)
    # c should appear (only in r2)
    chunks = [r.chunk for r in fused]
    assert "b" in chunks
    assert "c" in chunks
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/memory/test_search.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write MemorySearchManager**

```python
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
    chunk: str          # text snippet
    score: float       # fused score
    doc_path: str       # source file
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
        self._bm25_doc_freq: Dict[str, int] = {}  # term -> doc frequency
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
        """Hybrid search: BM25 + vector similarity with RRF fusion.

        Args:
            query: search query text
            top_k: number of results to return

        Returns:
            List of SearchResult sorted by fused score (descending)
        """
        # Load all memory/*.md files as documents
        docs = self._load_all_docs()
        if not docs:
            return []

        # Build BM25 index on first search
        if not self._bm25_doc_freq:
            self._build_bm25_index(docs)

        # BM25 scores
        bm25_results = self._bm25_search(query, docs)

        # Vector scores (if Ollama available)
        vector_results = []
        query_emb = await self.embed(query)
        if query_emb:
            vector_results = self._vector_search(query_emb, docs)

        # RRF fusion
        if vector_results:
            fused = self._rrf_fusion([bm25_results, vector_results], k=self._rrf_k)
        else:
            fused = bm25_results

        # Sort by score descending
        fused.sort(key=lambda r: r.score, reverse=True)
        return fused[:top_k]

    def _load_all_docs(self) -> List[Dict[str, Any]]:
        """Load all memory/*.md files as documents."""
        if not self.memory_dir.exists():
            return []
        docs = []
        for f in sorted(self.memory_dir.glob("*.md")):
            if f.name.startswith("."):
                continue
            content = f.read_text(encoding="utf-8")
            date_str = f.stem  # YYYY-MM-DD
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                date = datetime.now()
            # Split into chunks by session blocks
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
        """Build BM25 document frequency index."""
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
        """Tokenize text into terms (whitespace split, lowercase).

        Note: This is a simple tokenizer. For Chinese text, a proper
        segmentation library (jieba) would be better. This is a known
        limitation for the prototype phase.
        """
        return text.lower().split()

    def _bm25_score(self, query: str, doc: Dict[str, Any]) -> float:
        """Compute BM25 score for a document given a query."""
        tokens = self._tokenize(doc["chunk"])
        tf = Counter(tokens)
        query_tokens = self._tokenize(query)
        score = 0.0
        doc_len = len(tokens)
        for term in query_tokens:
            if term not in tf:
                continue
            n = self._bm25_doc_freq.get(term, 0)
            if n == 0:
                continue
            # IDF
            idf = math.log((self._total_docs - n + 0.5) / (n + 0.5) + 1)
            # TF component
            tf_val = tf[term]
            tf_component = (tf_val * (self._bm25_k1 + 1)) / (
                tf_val + self._bm25_k1 * (1 - self._bm25_b + self._bm25_b * doc_len / self._avgdl_or_avgdl())
            )
            score += idf * tf_component
        return score

    def _avgdl_or_avgdl(self) -> float:
        return self._bm25_avgdl if self._bm25_avgdl > 0 else 1.0

    def _bm25_search(self, query: str, docs: List[Dict[str, Any]]) -> List[SearchResult]:
        """Return BM25 scores for all docs sorted by score descending."""
        results = []
        for doc in docs:
            score = self._bm25_score(query, doc)
            if score > 0:
                score = self._apply_temporal_decay(score, doc["date"])
                results.append(SearchResult(chunk=doc["chunk"][:200], score=score, doc_path=doc["doc_path"], date=doc["date"]))
        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def _vector_score(self, query_emb: List[float], doc_emb: List[float]) -> float:
        """Cosine similarity between two vectors."""
        if not query_emb or not doc_emb or len(query_emb) != len(doc_emb):
            return 0.0
        dot = sum(a * b for a, b in zip(query_emb, doc_emb))
        norm_q = math.sqrt(sum(a * a for a in query_emb))
        norm_d = math.sqrt(sum(a * a for a in doc_emb))
        if norm_q == 0 or norm_d == 0:
            return 0.0
        return dot / (norm_q * norm_d)

    async def _vector_search(self, query_emb: List[float], docs: List[Dict[str, Any]]) -> List[SearchResult]:
        """Compute vector similarity scores for all docs."""
        results = []
        for doc in docs:
            # Try to get cached embedding or compute
            cache_key = f"{doc['doc_path']}:{hash(doc['chunk'][:100])}"
            if cache_key in self._embedding_cache:
                doc_emb = self._embedding_cache[cache_key]
            else:
                doc_emb = await self.embed(doc["chunk"][:500])  # truncate for speed
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
        """Reciprocal Rank Fusion to combine multiple rankings.

        RRF score = sum(1 / (k + rank)) for each ranking the result appears in.
        """
        rrf_scores: Dict[str, float] = {}
        chunk_to_result: Dict[str, SearchResult] = {}

        for ranking in rankings:
            for rank, result in enumerate(ranking):
                chunk_key = f"{result.doc_path}:{result.chunk[:50]}"
                if chunk_key not in rrf_scores:
                    rrf_scores[chunk_key] = 0.0
                    chunk_to_result[chunk_key] = result
                rrf_scores[chunk_key] += 1.0 / (k + rank + 1)  # +1 because rank is 0-indexed

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
        """Apply temporal decay to older documents.

        Documents older than rag_temporal_decay_days get reduced scores.
        """
        if not doc_date:
            return score
        now = datetime.now()
        age_days = (now - doc_date).days
        if age_days <= 0:
            return score
        decay_factor = max(0.5, 1.0 - (age_days / self._temporal_decay_days))
        return score * decay_factor
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/memory/test_search.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/memory/search.py tests/memory/test_search.py
git commit -m "feat(memory): add MemorySearchManager with hybrid RAG (BM25 + Ollama vector)"
```

---

## Phase 5: Cleanup

### Task 13: Delete old memory components

**Files to DELETE:**
- `app/memory/long_term.py`
- `app/memory/session_persistence.py`
- `app/memory/daily_writer.py`
- `app/memory/sessions/` (entire directory)
- `app/memory/log/` (entire directory)
- `app/tools/preference_tools.py`
- `app/memory/session_manager.py` (simplify or delete)
- `data/memory.db` (if exists)

**Dependency:** Tasks 1-12 complete

- [ ] **Step 1: Verify all new components are working**

Before cleanup, run:
```bash
pytest tests/memory/ tests/agents/test_preference.py -v
```

- [ ] **Step 2: Delete old files**

```bash
rm app/memory/long_term.py
rm app/memory/session_persistence.py
rm app/memory/daily_writer.py
rm -rf app/memory/sessions/
rm -rf app/memory/log/
rm app/tools/preference_tools.py
# Keep session_manager.py but simplify it (remove persistence dependency)
```

- [ ] **Step 3: Simplify session_manager.py**

Read `app/memory/session_manager.py`. Remove the `self._persistence` dependency. Keep only in-memory session management (the `ConversationBufferMemory` per session). Remove JSONL loading.

Simplified version:
```python
# app/memory/session_manager.py
"""SessionMemoryManager - in-memory session management only.

JSONL persistence removed in favor of Markdown daily logs.
This now only manages per-session ConversationBufferMemory instances in memory.
"""
from typing import Dict, Optional, List
from langchain_core.memory import ConversationBufferMemory
from pydantic import BaseModel


class SessionInfo(BaseModel):
    session_id: str
    history_count: int
    has_memory: bool


class SessionMemoryManager:
    """Manages in-memory ConversationBufferMemory per session (no persistence).

    Persistence now handled by DailyLogManager (Markdown files).
    """
    _instance: Optional["SessionMemoryManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._memories: Dict[str, ConversationBufferMemory] = {}
        return cls._instance

    def _create_memory(self) -> ConversationBufferMemory:
        return ConversationBufferMemory(
            return_messages=True,
            output_key="output",
            input_key="input",
        )

    def get_memory(self, session_id: str) -> ConversationBufferMemory:
        if session_id not in self._memories:
            self._memories[session_id] = self._create_memory()
        return self._memories[session_id]

    def clear_session(self, session_id: str) -> None:
        if session_id in self._memories:
            self._memories[session_id].clear()

    def has_memory(self, session_id: str) -> bool:
        if session_id not in self._memories:
            return False
        return len(self._memories[session_id].load_memory_variables({}).get("history", [])) > 0

    def get_history_count(self, session_id: str) -> int:
        if session_id not in self._memories:
            return 0
        return len(self._memories[session_id].load_memory_variables({}).get("history", []))

    def list_sessions(self) -> List[SessionInfo]:
        return [
            SessionInfo(
                session_id=sid,
                history_count=self.get_history_count(sid),
                has_memory=self.has_memory(sid),
            )
            for sid in self._memories
            if self.has_memory(sid)
        ]

    def clear_all(self) -> None:
        for mem in self._memories.values():
            mem.clear()
        self._memories.clear()


def get_session_memory_manager() -> SessionMemoryManager:
    return SessionMemoryManager()
```

- [ ] **Step 4: Update app/memory/__init__.py**

Update `app/memory/__init__.py` to re-export the new components:

```python
from app.memory.markdown_memory import MarkdownMemoryManager, get_markdown_memory_manager
from app.memory.daily_log import DailyLogManager, get_daily_log_manager
from app.memory.injector import MemoryInjector, get_memory_injector
from app.memory.search import MemorySearchManager
from app.memory.session_manager import SessionMemoryManager, get_session_memory_manager

__all__ = [
    "MarkdownMemoryManager",
    "get_markdown_memory_manager",
    "DailyLogManager",
    "get_daily_log_manager",
    "MemoryInjector",
    "get_memory_injector",
    "MemorySearchManager",
    "SessionMemoryManager",
    "get_session_memory_manager",
]
```

- [ ] **Step 5: Update app/main.py lifespan**

Remove SQLite initialization from lifespan. Update `app/main.py`:

Remove from imports:
```python
from app.memory.long_term import get_long_term_memory
```

Remove from lifespan:
```python
# OLD:
mem = get_long_term_memory(settings.database_url)
await mem.initialize()
yield
await mem.close()

# NEW:
yield  # No initialization needed for Markdown-based memory
```

Also remove the `os.makedirs` for database_url directory (no longer needed since no SQLite).

- [ ] **Step 6: Update chat_service.py to remove JSONL persistence**

Remove `from app.memory.session_persistence import get_session_persistence` and `self._persistence = get_session_persistence()`.

Remove the two `self._persistence.save_message(...)` calls in the `chat()` method (lines 89-100).

- [ ] **Step 7: Run tests to verify cleanup**

```bash
pytest tests/memory/ tests/agents/test_preference.py -v
```

- [ ] **Step 8: Commit**

```bash
git add -A app/memory/ app/tools/preference_tools.py app/main.py app/services/chat_service.py
git commit -m "chore(memory): remove SQLite/JSONL components, clean up old files"
```

---

## Phase 6: Frontend (Lower Priority)

### Task 14: Frontend Memory tab display

**Files:**
- Modify: `frontend/src/components/Sidebar.jsx`

**Dependency:** Tasks 1-13 complete

- [ ] This task is optional and lower priority. Only attempt if time permits.

The Memory tab should:
1. Fetch `GET /api/memory` (new endpoint — see below)
2. Display `MEMORY.md` content in a readable format
3. Add search functionality calling `POST /api/memory/search`

**New API endpoints needed (optional, lower priority):**
- `GET /api/memory` — return MEMORY.md content
- `POST /api/memory/search` — call MemorySearchManager.search()

---

## Summary of Tasks

| Phase | Task | Description | Files | Time |
|-------|------|-------------|-------|------|
| 1 | 1 | Config settings | `app/config.py` | 5 min |
| 1 | 2 | DailyLogManager | `app/memory/daily_log.py` | 30 min |
| 1 | 3 | MarkdownMemoryManager | `app/memory/markdown_memory.py` | 30 min |
| 1 | 4 | MemoryInjector | `app/memory/injector.py` | 20 min |
| 1 | 5 | Workspace files | `MEMORY.md`, `BOOTSTRAP.md`, `TOOLS.md` | 10 min |
| 2 | 6 | PreferenceAgent rewrite | `app/agents/preference.py` | 20 min |
| 2 | 7 | Supervisor update | `app/agents/supervisor.py` | 5 min |
| 2 | 8 | Session API rewrite | `app/api/session.py` | 20 min |
| 3 | 9 | ChatService integration | `app/services/chat_service.py` | 15 min |
| 3 | 10 | sys_prompt_builder | (no changes needed) | — |
| 3 | 11 | Supervisor plan() | (no changes needed) | — |
| 4 | 12 | MemorySearchManager | `app/memory/search.py` | 40 min |
| 5 | 13 | Cleanup old files | DELETE files | 20 min |
| 6 | 14 | Frontend Memory tab | `frontend/src/components/Sidebar.jsx` | (optional) |

**Total estimated time: ~3-4 hours**

---

## Testing Strategy

After all tasks complete, verify manually:

1. **Fresh session test**: Create new session, send "我想去成都3天，预算3000"
   - AI should respond (not know user yet)
   - Daily log `memory/YYYY-MM-DD.md` should have entry

2. **Preference persistence test**: In new session, say "我有心脏病，想节省一点"
   - AI should update MEMORY.md
   - Next session should know user has heart condition and prefers budgeting

3. **RAG search test**: Ask about past trip details
   - MemorySearchManager should retrieve relevant historical entries

4. **Session across days test**: Start session on day 1, continue on day 2
   - Session should have access to day 1's conversation via daily log
