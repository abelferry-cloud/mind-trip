# app/api/session.py
"""会话管理 API - 基于 Markdown daily logs 的会话接口。

参考：OpenClaw 的 memory/YYYY-MM-DD.md 会话追踪格式。
会话列表通过扫描 memory/ 文件中的 ## Session: 块生成。
"""
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

from app.services.memory import DailyLogManager, get_daily_log_manager

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
    """扫描所有 memory/logs/*.md 文件并提取唯一的会话。"""
    sessions = {}
    memory_dir = Path(__file__).parent.parent / "memory" / "logs"
    if not memory_dir.exists():
        return []

    import re
    for f in sorted(memory_dir.glob("*.md")):
        if f.name.startswith("."):
            continue
        content = f.read_text(encoding="utf-8")
        # 查找所有 ## Session: {id} 块
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
    # 返回新会话的空信息
    return SessionInfo(session_id=session_id, history_count=0, has_memory=False)


@router.get("/{session_id}/messages", response_model=SessionMessagesResponse)
async def get_session_messages(session_id: str):
    """获取会话的所有历史消息。"""
    session_content = _daily_mgr.read_session(session_id)
    if not session_content:
        return SessionMessagesResponse(session_id=session_id, messages=[])

    messages = []
    import re
    # 解析每个 [HH:MM:SS] Human: / AI: 块
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
    # 将删除标记追加到今日日志
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    marker = f"\n## Session: {session_id} [DELETED]\n"
    memory_dir = Path(__file__).parent.parent / "memory" / "logs"
    day_file = memory_dir / f"{date_str}.md"
    if day_file.exists():
        with open(day_file, "a", encoding="utf-8") as f:
            f.write(marker)

    # 更新 .deleted 索引
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
