"""会话记忆管理器 - 按 session_id 管理 ConversationBufferMemory 实例。"""

from typing import Dict, Optional, List
from langchain_classic.memory import ConversationBufferMemory as BaseConversationBufferMemory
from langchain_core.messages import BaseMessage


class ConversationBufferMemory(BaseConversationBufferMemory):
    """扩展 langchain_classic 的 ConversationBufferMemory，添加 get_history() 方法。"""

    def get_history(self) -> List[BaseMessage]:
        """获取对话历史消息列表。"""
        return self.load_memory_variables({})['history']


class SessionMemoryManager:
    """管理会话级的 ConversationBufferMemory 实例。

    每个 session_id 对应一个独立的 ConversationBufferMemory，
    确保不同会话的记忆相互隔离。
    """

    def __init__(self):
        self._memories: Dict[str, ConversationBufferMemory] = {}

    def get_memory(self, session_id: str) -> ConversationBufferMemory:
        """获取指定 session_id 的 memory 实例，不存在则创建。"""
        if session_id not in self._memories:
            self._memories[session_id] = ConversationBufferMemory(
                return_messages=True,
                output_key="output",
                input_key="input",
            )
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

    def clear_all(self) -> None:
        """清除所有 session 的记忆。"""
        for mem in self._memories.values():
            mem.clear()
        self._memories.clear()