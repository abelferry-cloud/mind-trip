"""Chat 服务 - 基于动态 System Prompt + 模型思考的对话服务。

核心流程（参考 OpenClaw 的上下文分层）：
1. 每次请求时，通过 WorkspacePromptLoader 动态加载 workspace/*.md
2. 将 system_prompt + user_message 发送给模型
3. 返回模型的回复

包含：记忆存储（SessionMemoryManager + DailyMemoryWriter）
"""
from typing import Optional, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from app.graph.sys_prompt_builder import get_supervisor_loader
from app.services.model_router import get_model_router
from app.memory.session_manager import SessionMemoryManager
from app.memory.daily_writer import DailyMemoryWriter


class ChatService:
    """对话服务。

    设计原则：
    - 每次请求时动态加载 system prompt（读取 workspace/*.md）
    - 通过 ModelRouter 调用模型
    - 通过 SessionMemoryManager 管理会话级记忆
    - 通过 DailyMemoryWriter 写入每日日志
    """

    def __init__(self):
        self._prompt_loader = get_supervisor_loader(mode="main")
        self._router = get_model_router()
        self._memory_manager = SessionMemoryManager()
        self._daily_writer = DailyMemoryWriter()

    async def chat(self, user_id: str, session_id: str, message: str) -> dict:
        """处理用户对话请求。

        Args:
            user_id:   用户 ID
            session_id: 会话 ID
            message:    用户发送的消息

        Returns:
            {
                "answer": 模型回复文本,
                "system_prompt": 动态加载的 system prompt,
                "model_used": 使用的模型名称,
                "workspace_loaded_at": 加载时间戳,
            }
        """
        # 1. 动态加载 system prompt（每次请求时重新读取 workspace/*.md）
        prompt_result = self._prompt_loader.invoke({
            "user_id": user_id,
            "session_id": session_id,
        })
        system_prompt = prompt_result["system_prompt"]
        workspace_loaded_at = prompt_result["workspace_loaded_at"]

        # 2. 获取对话历史并格式化
        mem = self._memory_manager.get_memory(session_id)
        history = mem.get_history()
        formatted_history = self._format_history(history)

        # 3. 将 history 追加到 system prompt
        full_system = system_prompt
        if formatted_history:
            full_system = f"{system_prompt}\n\n## 对话历史\n{formatted_history}"

        # 4. 将 full_system + user_message 发送给模型
        model_used = self._detect_model()
        answer = await self._router.call(
            prompt=message,
            system=full_system,
        )

        # 5. 保存对话到记忆
        mem.save_context({"input": message}, {"output": answer})
        self._daily_writer.append(
            session_id=session_id,
            user_id=user_id,
            human_message=message,
            ai_message=answer,
        )

        return {
            "answer": answer,
            "system_prompt": system_prompt,
            "model_used": model_used,
            "workspace_loaded_at": workspace_loaded_at,
        }

    def _format_history(self, history: List[BaseMessage]) -> str:
        """将对话历史格式化为字符串。

        Args:
            history: BaseMessage 列表（来自 ConversationBufferMemory）

        Returns:
            格式化后的历史字符串，每条消息占一行
        """
        if not history:
            return ""
        lines = []
        for msg in history:
            if isinstance(msg, HumanMessage):
                lines.append(f"Human: {msg.content}")
            elif isinstance(msg, AIMessage):
                lines.append(f"AI: {msg.content}")
            else:
                lines.append(f"{msg.type}: {msg.content}")
        return "\n".join(lines)

    def _detect_model(self) -> str:
        """检测当前使用的模型（基于配置）。"""
        from app.config import get_settings
        settings = get_settings()
        chain = settings.model_chain_list
        return chain[0] if chain else "unknown"


# 单例
_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
