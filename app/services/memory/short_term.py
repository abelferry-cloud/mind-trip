# app/services/memory/short_term.py
"""简单的短期记忆实现（legacy）。

注意：主要使用 session_manager.py 中的 ConversationBufferMemory。
此文件保留作为轻量级场景的备用。
"""
from typing import List, Optional


class SimpleMessage:
    """简单的消息类，用于模仿 LangChain 消息接口。"""
    def __init__(self, content: str, type: str):
        self.content = content
        self.type = type

    def __repr__(self):
        return f"SimpleMessage(type={self.type}, content={self.content[:30]}...)"


class HumanMessage(SimpleMessage):
    def __init__(self, content: str):
        super().__init__(content, "human")


class AIMessage(SimpleMessage):
    def __init__(self, content: str):
        super().__init__(content, "ai")


class ShortTermMemory:
    """简单的短期记忆存储。"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._messages: List[SimpleMessage] = []

    def save_context(self, inputs: dict, outputs: dict):
        """保存输入输出到记忆。"""
        input_text = inputs.get("input", "")
        output_text = outputs.get("output", "")
        self._messages.append(HumanMessage(input_text))
        self._messages.append(AIMessage(output_text))

    def get_messages(self) -> List[SimpleMessage]:
        """获取所有消息。"""
        return self._messages

    def get_context(self) -> str:
        """获取格式化的对话上下文。"""
        history = []
        for msg in self._messages:
            if isinstance(msg, HumanMessage):
                history.append(f"Human: {msg.content}")
            elif isinstance(msg, AIMessage):
                history.append(f"AI: {msg.content}")
        return "\n".join(history)

    def clear(self):
        """清除所有消息。"""
        self._messages.clear()


_short_term_stores: dict = {}


def get_short_term_memory(session_id: str) -> ShortTermMemory:
    """获取或创建指定 session_id 的短期记忆。"""
    if session_id not in _short_term_stores:
        _short_term_stores[session_id] = ShortTermMemory(session_id)
    return _short_term_stores[session_id]
