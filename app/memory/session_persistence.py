"""SessionPersistenceManager - JSONL 文件存储会话消息

类比 OpenClaw 的 ~/.openclaw/agents/<agentId>/sessions/<sessionId>.jsonl

文件结构:
    app/memory/sessions/           # JSONL 存储目录（自动创建）
      sessions.json                # 会话索引
      <session_id>.jsonl          # 每条消息一行
"""

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from filelock import FileLock


class SessionPersistenceManager:
    """JSONL 文件存储的会话持久化管理器

    使用文件锁保证并发安全，sessions.json 使用临时文件再 rename 保证原子性。
    """

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = Path(__file__).parent / "sessions"
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

        self._index_file = self._base_dir / "sessions.json"
        self._lock_file = self._base_dir / ".sessions.lock"

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        user_id: Optional[str] = None,
    ) -> None:
        """保存一条消息到指定会话的 JSONL 文件。

        Args:
            session_id: 会话 ID
            role: 角色，"human" 或 "ai"
            content: 消息内容
            user_id: 用户 ID（human 消息时有值，ai 消息时为 None）
        """
        if role not in ("human", "ai"):
            raise ValueError(f"role must be 'human' or 'ai', got '{role}'")

        session_file = self._base_dir / f"{session_id}.jsonl"

        # 构建消息记录
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
        }

        # 使用文件锁保护写入
        lock = FileLock(str(self._lock_file), timeout=10)
        with lock:
            # 追加写入 JSONL 文件
            with open(session_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(message, ensure_ascii=False) + "\n")

            # 更新索引
            self._update_index(session_id)

    def load_session(self, session_id: str) -> List[Dict]:
        """加载指定会话的所有消息。

        Args:
            session_id: 会话 ID

        Returns:
            消息列表，每条消息是一个 dict
        """
        session_file = self._base_dir / f"{session_id}.jsonl"

        if not session_file.exists():
            return []

        messages = []
        lock = FileLock(str(self._lock_file), timeout=10)
        with lock:
            with open(session_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        messages.append(json.loads(line))

        return messages

    def list_sessions(self) -> Dict:
        """列出所有会话及其元信息。

        Returns:
            字典，key 为 session_id，value 包含 created_at, updated_at, message_count
        """
        return self._load_index()

    def delete_session(self, session_id: str) -> None:
        """删除指定会话的所有数据。

        Args:
            session_id: 会话 ID
        """
        session_file = self._base_dir / f"{session_id}.jsonl"

        lock = FileLock(str(self._lock_file), timeout=10)
        with lock:
            # 删除 session 文件
            if session_file.exists():
                session_file.unlink()

            # 从索引中移除
            index = self._load_index()
            if session_id in index:
                del index[session_id]
                self._save_index(index)

    def _rebuild_index(self) -> None:
        """重建索引 - 扫描所有 .jsonl 文件重建 sessions.json

        用于 sessions.json 损坏时的恢复。
        """
        lock = FileLock(str(self._lock_file), timeout=10)
        with lock:
            index: Dict[str, Dict] = {}

            # 扫描所有 .jsonl 文件
            for session_file in self._base_dir.glob("*.jsonl"):
                if session_file.name == "sessions.json":
                    continue

                session_id = session_file.stem
                message_count = 0
                created_at = None
                updated_at = None

                # 读取文件获取统计信息
                try:
                    with open(session_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                msg = json.loads(line)
                                message_count += 1
                                ts = msg.get("timestamp")
                                if ts:
                                    if created_at is None or ts < created_at:
                                        created_at = ts
                                    if updated_at is None or ts > updated_at:
                                        updated_at = ts
                except (json.JSONDecodeError, IOError):
                    # 跳过损坏的文件
                    continue

                if message_count > 0:
                    index[session_id] = {
                        "created_at": created_at,
                        "updated_at": updated_at,
                        "message_count": message_count,
                    }

            self._save_index(index)

    def _load_index(self) -> Dict:
        """加载 sessions.json 索引文件。

        Returns:
            索引字典，如果文件不存在或损坏则返回空字典
        """
        if not self._index_file.exists():
            return {}

        try:
            with open(self._index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # 文件损坏，返回空字典
            return {}

    def _save_index(self, index: Dict) -> None:
        """保存索引到 sessions.json（原子性：先写临时文件再 rename）。

        Args:
            index: 索引字典
        """
        # 写入临时文件
        temp_file = self._index_file.with_suffix(".json.tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

        # 原子性替换
        if temp_file.exists():
            temp_file.replace(self._index_file)

    def _update_index(self, session_id: str) -> None:
        """更新指定会话在索引中的信息。

        Args:
            session_id: 会话 ID
        """
        index = self._load_index()
        session_file = self._base_dir / f"{session_id}.jsonl"

        # 计算当前文件的消息数和最新时间
        message_count = 0
        created_at = None
        updated_at = None

        if session_file.exists():
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            msg = json.loads(line)
                            message_count += 1
                            ts = msg.get("timestamp")
                            if ts:
                                if created_at is None or ts < created_at:
                                    created_at = ts
                                if updated_at is None or ts > updated_at:
                                    updated_at = ts
            except (json.JSONDecodeError, IOError):
                pass

        # 更新索引
        if session_id in index:
            existing = index[session_id]
            # 如果新消息的 created_at 更早，保留原有的
            if existing.get("created_at") and created_at:
                if existing["created_at"] < created_at:
                    created_at = existing["created_at"]
        else:
            # 新会话，使用当前时间
            if created_at is None:
                created_at = datetime.now(timezone.utc).isoformat()
            if updated_at is None:
                updated_at = created_at

        index[session_id] = {
            "created_at": created_at,
            "updated_at": updated_at,
            "message_count": message_count,
        }

        self._save_index(index)


# 单例
_persistence: Optional["SessionPersistenceManager"] = None


def get_session_persistence() -> SessionPersistenceManager:
    """获取全局唯一的 SessionPersistenceManager 实例。"""
    global _persistence
    if _persistence is None:
        _persistence = SessionPersistenceManager()
    return _persistence
