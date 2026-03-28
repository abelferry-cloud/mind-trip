"""会话记忆管理器 - 按 session_id 管理 ConversationBufferMemory 实例。"""

from typing import Dict, Optional, List
from langchain_classic.memory import ConversationBufferMemory as BaseConversationBufferMemory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from pydantic import BaseModel


# ConversationBufferMemory key constants
DEFAULT_OUTPUT_KEY = "output"
DEFAULT_INPUT_KEY = "input"


class SessionInfo(BaseModel):
    """会话信息（与 API 层解耦，避免循环导入）。"""
    session_id: str
    history_count: int
    has_memory: bool


class ConversationBufferMemory(BaseConversationBufferMemory):
    """扩展 langchain_classic 的 ConversationBufferMemory，添加 get_history() 方法。"""

    def get_history(self) -> List[BaseMessage]:
        """获取对话历史消息列表。"""
        return self.load_memory_variables({})['history']


class SessionMemoryManager:
    """管理会话级的 ConversationBufferMemory 实例（单例）。

    每个 session_id 对应一个独立的 ConversationBufferMemory，
    确保不同会话的记忆相互隔离。
    """

    _instance: Optional["SessionMemoryManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._memories: Dict[str, ConversationBufferMemory] = {}
        return cls._instance

    def _create_memory(self) -> ConversationBufferMemory:
        """Create a new ConversationBufferMemory instance with default keys."""
        return ConversationBufferMemory(
            return_messages=True,
            output_key=DEFAULT_OUTPUT_KEY,
            input_key=DEFAULT_INPUT_KEY,
        )

    def get_memory(self, session_id: str) -> ConversationBufferMemory:
        """获取指定 session_id 的 memory 实例，不存在则创建。"""
        if session_id not in self._memories:
            self._memories[session_id] = self._create_memory()
        return self._memories[session_id]

    def clear_session(self, session_id: str) -> None:
        """清除指定 session 的记忆。"""
        if session_id in self._memories:
            self._memories[session_id].clear()

    def has_memory(self, session_id: str) -> bool:
        """检查指定 session 是否有记忆。"""
        if session_id not in self._memories:
            return False
        return len(self._memories[session_id].get_history()) > 0

    def get_history_count(self, session_id: str) -> int:
        """获取指定 session 的历史消息数量。"""
        if session_id not in self._memories:
            return 0
        return len(self._memories[session_id].get_history())

    def list_sessions(self) -> List[SessionInfo]:
        """返回所有有记忆的会话列表。"""
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
        """清除所有 session 的记忆。"""
        for mem in self._memories.values():
            mem.clear()
        self._memories.clear()


def get_session_memory_manager() -> SessionMemoryManager:
    """获取全局唯一的 SessionMemoryManager 实例。"""
    return SessionMemoryManager()
