# app/api/session.py
"""会话管理 API - 增删查会话接口。"""
import uuid
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from langchain_core.messages import HumanMessage, AIMessage
from app.memory.session_manager import get_session_memory_manager, SessionInfo
from app.memory.session_persistence import get_session_persistence

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

_memory_manager = get_session_memory_manager()


class CreateSessionResponse(BaseModel):
    session_id: str


class DeleteSessionResponse(BaseModel):
    success: bool
    message: str


class MessageItem(BaseModel):
    role: str  # "human" | "ai"
    content: str


class SessionMessagesResponse(BaseModel):
    session_id: str
    messages: List[MessageItem]


@router.post("", response_model=CreateSessionResponse)
async def create_session():
    """创建新会话。

    Returns:
        新创建的 session_id
    """
    session_id = str(uuid.uuid4())
    _memory_manager.get_memory(session_id)
    return CreateSessionResponse(session_id=session_id)


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    """获取会话信息。

    Args:
        session_id: 会话 ID

    Returns:
        会话信息（消息数量、是否有记忆）
    """
    return SessionInfo(
        session_id=session_id,
        history_count=_memory_manager.get_history_count(session_id),
        has_memory=_memory_manager.has_memory(session_id),
    )


@router.get("/{session_id}/messages", response_model=SessionMessagesResponse)
async def get_session_messages(session_id: str):
    """获取会话的所有历史消息。

    Args:
        session_id: 会话 ID

    Returns:
        会话消息列表
    """
    mem = _memory_manager.get_memory(session_id)
    history = mem.get_history()

    messages = []
    for msg in history:
        if isinstance(msg, HumanMessage):
            messages.append(MessageItem(role="human", content=msg.content))
        elif isinstance(msg, AIMessage):
            messages.append(MessageItem(role="ai", content=msg.content))
        else:
            messages.append(MessageItem(role=msg.type, content=msg.content))

    return SessionMessagesResponse(session_id=session_id, messages=messages)


@router.get("", response_model=List[SessionInfo])
async def list_sessions():
    """列出所有会话（仅返回有记忆的会话）。

    Returns:
        所有有历史消息的会话列表
    """
    return _memory_manager.list_sessions()


@router.delete("/{session_id}", response_model=DeleteSessionResponse)
async def delete_session(session_id: str):
    """删除会话（清除会话记忆）。

    Args:
        session_id: 会话 ID

    Returns:
        删除结果
    """
    _memory_manager.clear_session(session_id)
    persistence = get_session_persistence()
    persistence.delete_session(session_id)
    return DeleteSessionResponse(success=True, message=f"Session {session_id} 已清除")
