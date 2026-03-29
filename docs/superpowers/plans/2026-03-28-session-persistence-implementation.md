# 会话持久化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 SessionMemoryManager 的内存存储持久化到 JSONL 文件，实现服务重启后会话恢复

**Architecture:** 新增 SessionPersistenceManager 类管理 JSONL 文件读写，修改 SessionMemoryManager 在启动时恢复会话，在 save_context 后同步写入 JSONL

**Tech Stack:** Python 文件锁（filelock）、JSONL、ConversationBufferMemory

---

## 文件结构

```
app/memory/
  session_persistence.py   # 新增：SessionPersistenceManager
  session_manager.py      # 修改：集成持久化
  sessions/               # 新增：JSONL 存储目录
    sessions.json
    <session_id>.jsonl
```

---

## Task 1: 创建 SessionPersistenceManager

**Files:**
- Create: `app/memory/session_persistence.py`
- Test: `tests/memory/test_session_persistence.py`

- [ ] **Step 1: 写测试**

```python
# tests/memory/test_session_persistence.py
import os
import tempfile
import uuid
from app.memory.session_persistence import SessionPersistenceManager

def test_save_and_load_message():
    with tempfile.TemporaryDirectory() as tmpdir:
        pm = SessionPersistenceManager(base_dir=tmpdir)
        session_id = str(uuid.uuid4())

        # 追加 human 消息
        pm.save_message(session_id, "human", "你好", user_id="user_1")
        # 追加 ai 消息
        pm.save_message(session_id, "ai", "你好！", user_id=None)

        # 读取验证
        messages = pm.load_session(session_id)
        assert len(messages) == 2
        assert messages[0]["role"] == "human"
        assert messages[0]["content"] == "你好"
        assert messages[1]["role"] == "ai"

        # sessions.json 验证
        sessions = pm.list_sessions()
        assert session_id in sessions
        assert sessions[session_id]["message_count"] == 2

def test_delete_session():
    with tempfile.TemporaryDirectory() as tmpdir:
        pm = SessionPersistenceManager(base_dir=tmpdir)
        session_id = str(uuid.uuid4())

        pm.save_message(session_id, "human", "test", user_id="u1")
        assert os.path.exists(os.path.join(tmpdir, f"{session_id}.jsonl"))

        pm.delete_session(session_id)
        assert not os.path.exists(os.path.join(tmpdir, f"{session_id}.jsonl"))
        assert session_id not in pm.list_sessions()

def test_rebuild_index():
    with tempfile.TemporaryDirectory() as tmpdir:
        pm = SessionPersistenceManager(base_dir=tmpdir)
        sid1, sid2 = str(uuid.uuid4()), str(uuid.uuid4())

        pm.save_message(sid1, "human", "msg1", user_id="u1")
        pm.save_message(sid2, "human", "msg2", user_id="u2")

        # 模拟 sessions.json 损坏
        with open(os.path.join(tmpdir, "sessions.json"), "w") as f:
            f.write("corrupted")

        # _rebuild_index 应能从 JSONL 重建
        pm._rebuild_index()
        sessions = pm.list_sessions()
        assert sid1 in sessions
        assert sid2 in sessions
```

- [ ] **Step 2: 运行测试，确认失败（模块不存在）**

Run: `pytest tests/memory/test_session_persistence.py -v`
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: 实现 SessionPersistenceManager**

```python
# app/memory/session_persistence.py
"""会话持久化管理器 - JSONL 文件存储。"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Literal

from filelock import FileLock


class SessionPersistenceManager:
    """管理会话消息的 JSONL 持久化。

    文件结构：
    - sessions.json: 会话索引
    - <session_id>.jsonl: 每条消息一行
    """

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = Path(__file__).parent / "sessions"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._sessions_file = self.base_dir / "sessions.json"
        self._lock_file = self.base_dir / ".lock"

    def _load_index(self) -> Dict:
        """加载 sessions.json，不存在则返回空字典。"""
        if not self._sessions_file.exists():
            return {}
        try:
            return json.loads(self._sessions_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_index(self, index: Dict) -> None:
        """原子性写入 sessions.json（先写临时文件再 rename）。"""
        tmp = self._sessions_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self._sessions_file)

    def save_message(
        self,
        session_id: str,
        role: Literal["human", "ai"],
        content: str,
        user_id: Optional[str] = None,
    ) -> None:
        """追加一条消息到 JSONL，同步更新 sessions.json。"""
        jsonl_file = self.base_dir / f"{session_id}.jsonl"
        now = datetime.now(timezone.utc).isoformat()

        record = {
            "role": role,
            "content": content,
            "timestamp": now,
            "user_id": user_id,
        }

        lock = FileLock(str(self._lock_file), timeout=10)
        with lock:
            with open(jsonl_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

            index = self._load_index()
            if session_id not in index:
                index[session_id] = {
                    "created_at": now,
                    "updated_at": now,
                    "message_count": 0,
                }
            index[session_id]["updated_at"] = now
            index[session_id]["message_count"] = index[session_id].get("message_count", 0) + 1
            self._save_index(index)

    def load_session(self, session_id: str) -> List[Dict]:
        """读取会话所有历史消息。"""
        jsonl_file = self.base_dir / f"{session_id}.jsonl"
        if not jsonl_file.exists():
            return []
        messages = []
        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    messages.append(json.loads(line))
        return messages

    def list_sessions(self) -> Dict:
        """返回会话索引。"""
        return self._load_index()

    def delete_session(self, session_id: str) -> None:
        """删除 JSONL 文件和索引。"""
        jsonl_file = self.base_dir / f"{session_id}.jsonl"
        if jsonl_file.exists():
            jsonl_file.unlink()

        index = self._load_index()
        if session_id in index:
            del index[session_id]
            self._save_index(index)

    def _rebuild_index(self) -> None:
        """扫描所有 .jsonl 文件，重建 sessions.json。"""
        index = {}
        for jsonl_file in self.base_dir.glob("*.jsonl"):
            sid = jsonl_file.stem
            messages = self.load_session(sid)
            if messages:
                last_ts = messages[-1]["timestamp"]
                index[sid] = {
                    "created_at": messages[0]["timestamp"],
                    "updated_at": last_ts,
                    "message_count": len(messages),
                }
        self._save_index(index)


# 单例
_persistence: Optional["SessionPersistenceManager"] = None


def get_session_persistence() -> SessionPersistenceManager:
    global _persistence
    if _persistence is None:
        _persistence = SessionPersistenceManager()
    return _persistence
```

- [ ] **Step 4: 运行测试，确认全部通过**

Run: `pytest tests/memory/test_session_persistence.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add app/memory/session_persistence.py tests/memory/test_session_persistence.py
git commit -m "feat(memory): add SessionPersistenceManager for JSONL storage"
```

---

## Task 2: 修改 SessionMemoryManager 集成持久化

**Files:**
- Modify: `app/memory/session_manager.py`
- Test: `tests/memory/test_session_manager.py`

- [ ] **Step 1: 写测试**

```python
# tests/memory/test_session_manager.py
import tempfile
from pathlib import Path
from app.memory.session_manager import SessionMemoryManager
from app.memory.session_persistence import get_session_persistence

def test_restore_from_jsonl():
    with tempfile.TemporaryDirectory() as tmpdir:
        # 模拟已有 JSONL 数据
        persistence = get_session_persistence()
        original_persistence = persistence._persistence
        persistence._persistence = type(persistence)(base_dir=tmpdir)

        sid = "test-session-123"
        persistence.save_message(sid, "human", "你好", user_id="u1")
        persistence.save_message(sid, "ai", "你好！", user_id=None)

        # 重启后从 JSONL 恢复
        manager = SessionMemoryManager()
        manager._persistence = persistence

        mem = manager.get_memory(sid)
        history = mem.get_history()
        assert len(history) == 2
        assert "你好" in history[0].content

        persistence._persistence = original_persistence
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `pytest tests/memory/test_session_manager.py -v`
Expected: FAIL

- [ ] **Step 3: 修改 SessionMemoryManager**

```python
# app/memory/session_manager.py 修改点：
# 1. __init__ 中添加 _persistence 和 _restore_all_sessions()
# 2. get_memory 中添加从 JSONL 加载逻辑
# 3. save_context 后调用 persistence.save_message
```

```python
# 在 session_manager.py 顶部添加导入
from app.memory.session_persistence import get_session_persistence, SessionPersistenceManager

# SessionMemoryManager.__init__ 修改：
def __new__(cls):
    if cls._instance is None:
        cls._instance = super().__new__(cls)
        cls._instance._memories: Dict[str, ConversationBufferMemory] = {}
        cls._instance._persistence = get_session_persistence()
        cls._instance._restored = False
    return cls._instance

def _restore_all_sessions(self) -> None:
    """启动时从 JSONL 恢复所有会话。"""
    if self._restored:
        return
    self._restored = True
    sessions = self._persistence.list_sessions()
    for session_id in sessions:
        self._load_session_from_jsonl(session_id)

def _load_session_from_jsonl(self, session_id: str) -> None:
    """从 JSONL 加载单个会话到内存。"""
    if session_id in self._memories:
        return
    messages = self._persistence.load_session(session_id)
    if not messages:
        return
    mem = ConversationBufferMemory(
        return_messages=True,
        output_key="output",
        input_key="input",
    )
    # 批量加载历史
    for msg in messages:
        if msg["role"] == "human":
            from langchain_core.messages import HumanMessage
            mem.chat_memory.messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "ai":
            from langchain_core.messages import AIMessage
            mem.chat_memory.messages.append(AIMessage(content=msg["content"]))
    self._memories[session_id] = mem

# SessionMemoryManager.get_memory 修改：
def get_memory(self, session_id: str) -> ConversationBufferMemory:
    self._restore_all_sessions()  # 启动恢复
    if session_id not in self._memories:
        self._memories[session_id] = ConversationBufferMemory(
            return_messages=True,
            output_key="output",
            input_key="input",
        )
        # 尝试从 JSONL 恢复
        self._load_session_from_jsonl(session_id)
    return self._memories[session_id]
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `pytest tests/memory/test_session_manager.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add app/memory/session_manager.py tests/memory/test_session_manager.py
git commit -m "feat(memory): integrate SessionPersistenceManager into SessionMemoryManager"
```

---

## Task 3: 修改 ChatService 同步写入 JSONL

**Files:**
- Modify: `app/services/chat_service.py`

- [ ] **Step 1: 确认 ChatService 调用位置**

`chat()` 方法在 `mem.save_context()` 后已调用 `daily_writer.append()`，需在此之后同步调用 `persistence.save_message()`

- [ ] **Step 2: 修改 chat_service.py**

```python
# 在 ChatService.__init__ 中添加 self._persistence = get_session_persistence()
# 在 chat() 方法中，save_context 后添加：

# 同步写入 JSONL
from langchain_core.messages import HumanMessage, AIMessage
self._persistence.save_message(
    session_id=session_id,
    role="human",
    content=message,
    user_id=user_id,
)
self._persistence.save_message(
    session_id=session_id,
    role="ai",
    content=answer,
    user_id=None,
)
```

- [ ] **Step 3: 验证代码正确性**

Run: `python -c "from app.services.chat_service import get_chat_service; print('OK')"`
Expected: 无报错

- [ ] **Step 4: 提交**

```bash
git add app/services/chat_service.py
git commit -m "feat(chat_service): sync write to JSONL after save_context"
```

---

## Task 4: 修改 API 删除会话时清理 JSONL

**Files:**
- Modify: `app/api/session.py`

- [ ] **Step 1: 修改 delete_session 端点**

```python
from app.memory.session_persistence import get_session_persistence

@router.delete("/{session_id}", response_model=DeleteSessionResponse)
async def delete_session(session_id: str):
    _memory_manager.clear_session(session_id)
    persistence = get_session_persistence()
    persistence.delete_session(session_id)
    return DeleteSessionResponse(success=True, message=f"Session {session_id} 已清除")
```

- [ ] **Step 2: 验证**

Run: `python -c "from app.api.session import router; print('OK')"`
Expected: 无报错

- [ ] **Step 3: 提交**

```bash
git add app/api/session.py
git commit -m "feat(api): delete JSONL when session is deleted"
```

---

## Task 5: 集成测试

**Files:**
- Create: `tests/memory/test_integration_persistence.py`

- [ ] **Step 1: 写集成测试**

```python
"""会话持久化端到端测试。"""
import tempfile
import os
from pathlib import Path
from app.memory.session_manager import SessionMemoryManager
from app.memory.session_persistence import get_session_persistence, SessionPersistenceManager

def test_full_lifecycle():
    """测试创建 → 发送消息 → 重启 → 恢复。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 第一次：创建会话，写入消息
        persistence = SessionPersistenceManager(base_dir=tmpdir)
        manager1 = SessionMemoryManager()
        manager1._persistence = persistence

        sid = "test-lifecycle"
        mem1 = manager1.get_memory(sid)
        mem1.save_context({"input": "你好"}, {"output": "你好！"})

        # 验证已写入 JSONL
        jsonl_file = Path(tmpdir) / f"{sid}.jsonl"
        assert jsonl_file.exists()

        # 第二次：模拟重启，新实例从 JSONL 恢复
        manager2 = SessionMemoryManager()
        manager2._persistence = persistence
        manager2._restored = False  # 重置恢复标记

        mem2 = manager2.get_memory(sid)
        history = mem2.get_history()
        assert len(history) == 2
        assert "你好" in history[0].content
        assert "你好！" in history[1].content
```

- [ ] **Step 2: 运行集成测试**

Run: `pytest tests/memory/test_integration_persistence.py -v`
Expected: PASS

- [ ] **Step 3: 提交**

```bash
git add tests/memory/test_integration_persistence.py
git commit -m "test: add session persistence integration test"
```

---

## 完成后验证

```bash
# 1. 确保所有测试通过
pytest tests/memory/ -v

# 2. 手动验证重启恢复
python -c "
from app.memory.session_manager import SessionMemoryManager
from app.memory.session_persistence import get_session_persistence

m = SessionMemoryManager()
p = get_session_persistence()
print('Sessions:', list(p.list_sessions().keys()))
print('OK')
"
```
