# OpenClaw Memory Architecture Migration Design

**Date**: 2026-03-28
**Status**: Draft
**Type**: Architecture Migration

---

## 1. Overview

### 1.1 Motivation

Current system has a critical cross-session memory gap: user preferences are written to SQLite but never read back into the system prompt. The AI sees empty placeholder templates in `USER.md` and `MEMORY.md`, making it unable to identify the user across sessions.

Reference: OpenClaw's "Markdown is Source of Truth" architecture.

### 1.2 Design Principle

**"Markdown 即真相" (Markdown is Source of Truth)**

- All memory stored in plain Markdown files
- No hidden state in databases
- Files are human-readable and git-tracked
- Model only "remembers" what gets written to disk
- System reads files at session start and injects into system prompt

### 1.3 Migration Scope

| Component | Action |
|-----------|--------|
| `app/memory/long_term.py` (SQLite) | Delete |
| `app/memory/session_persistence.py` (JSONL) | Delete |
| `app/tools/preference_tools.py` | Rewrite as Markdown writer |
| `app/agents/preference.py` | Redirect writes to Markdown |
| `app/graph/sys_prompt_builder.py` | Add memory injection layer |
| `app/services/chat_service.py` | Integrate memory loader |
| `app/api/session.py` | Adapt to Markdown-based session list |
| `memory/log/` → `memory/` | Restructure to `YYYY-MM-DD.md` |

---

## 2. Memory File Structure

### 2.1 Directory Layout

```
app/workspace/
├── MEMORY.md              # Curated long-term memory (user profile, preferences, key decisions)
├── memory/
│   ├── 2026-03-28.md      # Daily session log (append-only)
│   ├── 2026-03-27.md
│   └── ...
└── sessions/
    └── (deleted - no longer needed)
```

### 2.2 MEMORY.md Format

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

### 2.3 Daily Log Format (`memory/YYYY-MM-DD.md`)

```markdown
# 2026-03-28

## Session: abc123

[20:45:33]
Human: 我想去成都玩3天，预算3000
AI: 已为您规划成都3天行程，预算3000元...

## Session: def456

[21:10:15]
Human: 帮我看看成都的美食
AI: 成都必吃的美食有...
```

### 2.4 Session Init File Format

```markdown
# Session: abc123

## Created: 2026-03-28 20:45:00

## User: user_123

## Key Decisions

- 目的地：成都
- 天数：3天
- 预算：3000元

## Conversation

[20:45:33]
Human: 我想去成都玩3天，预算3000
AI: 已为您规划成都3天行程，预算3000元...

---
```

---

## 3. Architecture Components

### 3.1 New Components

| Component | File | Responsibility |
|-----------|------|----------------|
| `MarkdownMemoryManager` | `app/memory/markdown_memory.py` | Unified interface for reading/writing Markdown memory files |
| `DailyLogManager` | `app/memory/daily_log.py` | Append-only daily session logs |
| `MemorySearchManager` | `app/memory/search.py` | Hybrid RAG (vector + BM25) via Ollama |
| `MemoryInjector` | `app/memory/injector.py` | Compose memory content into system prompt |

### 3.2 Deleted Components

| Component | Reason |
|-----------|--------|
| `app/memory/long_term.py` | Replaced by Markdown files |
| `app/memory/session_persistence.py` | Replaced by Markdown daily logs |
| `app/tools/preference_tools.py` | Rewrite as direct Markdown writer |
| `data/memory.db` | Deleted, no migration |

---

## 4. Memory Flow

### 4.1 Write Flow (AI writes memory)

```
User Message → SupervisorAgent
                    ↓
            PreferenceAgent.parse_and_update()
                    ↓
            MarkdownMemoryManager.write_preference()
                    ↓
            Updates MEMORY.md (long-term)
            + Appends to memory/YYYY-MM-DD.md (daily log)
```

### 4.2 Read Flow (Session starts)

```
API Request: chat(user_id, session_id, message)
                    ↓
            MemoryInjector.load_session_memory()
                    ↓
            1. Read MEMORY.md (if mode="main")
            2. Read memory/YYYY-MM-DD.md (today)
            3. Read memory/YYYY-MM-DD.md (yesterday)
                    ↓
            Compose into system prompt context block
                    ↓
            Supervisor sees user profile + recent history
```

### 4.3 Search Flow (RAG retrieval)

```
User Query → MemorySearchManager.search(query)
                    ↓
            1. Ollama qwen3-embedding:0.6b → query vector
            2. Load all memory/*.md files
            3. BM25 keyword search
            4. Vector similarity search (top-k)
            5. Hybrid fusion (RRF + temporal decay)
                    ↓
            Return top relevant chunks
                    ↓
            Inject into system prompt as "Relevant Memory" section
```

---

## 5. Component Specifications

### 5.1 MarkdownMemoryManager

**File**: `app/memory/markdown_memory.py`

```python
class MarkdownMemoryManager:
    """Manages MEMORY.md - the curated long-term memory file."""

    def __init__(self, memory_path: Path):
        self.memory_path = memory_path

    async def get_memory(self) -> str:
        """Read MEMORY.md content."""

    async def update_user_profile(self, user_id: str, profile: dict) -> None:
        """Update user profile section in MEMORY.md."""

    async def append_decision(self, session_id: str, decision: str) -> None:
        """Append key decision to MEMORY.md under 'Key Decisions' section."""

    async def update_preference(self, user_id: str, category: str, value: Any) -> None:
        """Update specific preference category in MEMORY.md."""
```

### 5.2 DailyLogManager

**File**: `app/memory/daily_log.py`

```python
class DailyLogManager:
    """Append-only daily session logs at memory/YYYY-MM-DD.md."""

    def __init__(self, memory_dir: Path):
        self.memory_dir = memory_dir

    def append(self, session_id: str, user_id: str,
               human_message: str, ai_message: str) -> None:
        """Append a message pair to today's daily log."""

    def read_today_and_yesterday(self) -> str:
        """Read today's and yesterday's daily logs for session start."""

    def read_session(self, session_id: str) -> str:
        """Read all entries for a specific session across daily logs."""
```

### 5.3 MemorySearchManager

**File**: `app/memory/search.py`

```python
class MemorySearchManager:
    """Hybrid RAG: vector search (Ollama) + BM25 keyword search."""

    def __init__(self, memory_dir: Path, ollama_base_url: str = "http://localhost:11434"):
        self.memory_dir = memory_dir
        self.ollama_base_url = ollama_base_url
        self._embedding_cache: Dict[str, List[float]] = {}

    async def embed(self, text: str) -> List[float]:
        """Get embedding via Ollama qwen3-embedding:0.6b."""

    async def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """Hybrid search: BM25 + vector similarity with RRF fusion."""

    def _bm25_score(self, query: str, doc: str) -> float:
        """BM25 keyword search score."""

    def _vector_score(self, query_emb: List[float], doc_emb: List[float]) -> float:
        """Cosine similarity between vectors."""

    def _rrf_fusion(self, rankings: List[List[SearchResult]], k: int = 60) -> List[SearchResult]:
        """Reciprocal Rank Fusion for hybrid scoring."""

    def _temporal_decay(self, score: float, doc_date: datetime) -> float:
        """Apply temporal decay to older documents."""
```

**Embedding Config**:
- Model: `qwen3-embedding:0.6b` via Ollama
- Endpoint: `POST http://localhost:11434/api/embeddings`
- Batch embedding for daily log files on startup (cached in memory)

### 5.4 MemoryInjector

**File**: `app/memory/injector.py`

```python
class MemoryInjector:
    """Composes memory content into system prompt at session start."""

    def __init__(self,
                 memory_manager: MarkdownMemoryManager,
                 daily_log_manager: DailyLogManager,
                 search_manager: Optional[MemorySearchManager] = None):
        self.memory_manager = memory_manager
        self.daily_log_manager = daily_log_manager
        self.search_manager = search_manager

    async def load_session_memory(
        self,
        user_id: str,
        session_id: str,
        mode: Literal["main", "shared"],
        query: Optional[str] = None,
    ) -> str:
        """Load all relevant memory for a session and compose as string.

        Returns:
            Markdown string to inject into system prompt under '## Memory' section.
        """

    async def _compose_main_session_memory(self, user_id: str) -> str:
        """Compose memory for main private session (includes MEMORY.md)."""

    async def _compose_shared_session_memory(self, user_id: str) -> str:
        """Compose memory for shared session (no MEMORY.md)."""
```

### 5.5 PreferenceAgent Changes

**File**: `app/agents/preference.py`

Redirect all writes from SQLite to Markdown:

```python
class PreferenceAgent:
    """Now writes to Markdown files (MEMORY.md + daily log)."""

    async def update_preference(self, user_id: str, category: str, value: Any) -> Dict[str, bool]:
        # Write to MEMORY.md
        mem = get_markdown_memory_manager()
        await mem.update_preference(user_id, category, value)
        return {"success": True}

    async def parse_and_update(self, user_id: str, message: str) -> Dict[str, Any]:
        # Parse user message for preferences
        # Write to MEMORY.md + daily log
```

---

## 6. Workspace File Updates

### 6.1 BOOTSTRAP.md Changes

Current bootstrap is a one-time ceremony file. Update to reflect memory architecture:

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

### 6.2 TOOLS.md Changes

Add memory-related tool descriptions:

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

---

## 7. Session Management Changes

### 7.1 Session List API Change

Currently `GET /api/sessions` returns sessions from in-memory SessionMemoryManager (backed by JSONL).

After migration:
- Session list derived from daily log files (scan `memory/*.md`)
- Each session's `last_updated` from file modification time
- `history_count` parsed from session entries in daily logs

### 7.2 Session Messages API Change

Currently `GET /api/sessions/{session_id}/messages` loads from JSONL.

After migration:
- Read from `memory/*.md` files (across multiple daily logs if session spans days)
- Parse `## Session: {session_id}` blocks

### 7.3 Session Deletion API

Currently `DELETE /api/sessions/{session_id}` deletes JSONL file.

After migration:
- Mark session entries as "[deleted]" in daily logs (append-only, don't modify files)
- Add `deleted_sessions` tracking in a `memory/.deleted` index file

---

## 8. Configuration Changes

### 8.1 New Config in `app/config.py`

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # Memory
    memory_dir: str = "app/workspace/memory"      # Daily log directory
    memory_file: str = "app/workspace/MEMORY.md"  # Long-term memory file

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

---

## 9. Implementation Order

### Phase 1: Foundation (Core infrastructure)
1. Create `app/memory/markdown_memory.py` (MarkdownMemoryManager)
2. Create `app/memory/daily_log.py` (DailyLogManager)
3. Create `app/memory/injector.py` (MemoryInjector)
4. Update `app/workspace/` files (MEMORY.md template, BOOTSTRAP.md, TOOLS.md)
5. Update `app/config.py` with memory settings

### Phase 2: Redirect Writes (PreferenceAgent)
6. Rewrite `app/agents/preference.py` to write Markdown
7. Update `app/tools/preference_tools.py` → delete, functionality moved to MarkdownMemoryManager
8. Update `app/agents/supervisor.py` to use new preference flow

### Phase 3: Integrate Reads (Session start memory injection)
9. Integrate MemoryInjector into `app/services/chat_service.py`
10. Update `app/graph/sys_prompt_builder.py` to accept injected memory
11. Update `app/api/chat.py` to trigger memory load on session start

### Phase 4: RAG Search
12. Create `app/memory/search.py` (MemorySearchManager with Ollama embedding)
13. Add `search_memory` tool to agent toolset
14. Integrate into MemoryInjector (optional query-based retrieval)

### Phase 5: Cleanup (Remove old components)
15. Delete `app/memory/long_term.py`
16. Delete `app/memory/session_persistence.py`
17. Delete `app/memory/session_manager.py` (or simplify to in-memory only)
18. Update `app/api/session.py` to use Markdown-based session list
19. Delete `data/memory.db` and `app/memory/sessions/` directory
20. Update `app/main.py` lifespan to remove SQLite init

### Phase 6: Frontend (Optional session memory display)
21. Update frontend `Sidebar.jsx` "Memory" tab to display MEMORY.md content
22. Add memory search UI

---

## 10. Error Handling

### 10.1 Memory File Not Found
- `MEMORY.md` missing → create from template silently
- `memory/YYYY-MM-DD.md` missing → create empty file with date header

### 10.2 Ollama Unavailable
- If embedding service is down, fall back to BM25-only search
- Log warning, don't fail the request

### 10.3 Concurrent Writes
- Daily log appends use file locking (via `filelock` library)
- MEMORY.md updates use rename-to-write pattern (atomic)

---

## 11. Testing Strategy

### 11.1 Unit Tests
- `MarkdownMemoryManager`: read/write/update operations
- `DailyLogManager`: append, read today/yesterday, session parsing
- `MemorySearchManager`: BM25, vector scoring, RRF fusion

### 11.2 Integration Tests
- Session start memory injection end-to-end
- Preference update → MEMORY.md write → read back
- Daily log append across multiple sessions

### 11.3 Manual Verification
- Fresh session: AI sees empty MEMORY.md template
- After preference mention: AI updates MEMORY.md
- Next session: AI reads MEMORY.md and knows user info

---

## 12. Open Questions (Deferred)

- [ ] Frontend Memory tab UI design (not in scope for Phase 1-5)
- [ ] Session search across historical logs (query-based retrieval only in Phase 4)
- [ ] MEMORY.md compaction (when it grows too large) - future work

---

## 13. Reference

- OpenClaw Memory Documentation: https://docs.openclaw.ai/concepts/memory
- OpenClaw Source: `src/memory/` (GitHub)
- Ollama Embedding API: `POST /api/embeddings`
