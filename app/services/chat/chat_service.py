"""Chat 服务 - 基于动态 System Prompt + 模型思考的对话服务。

核心流程（参考 OpenClaw 的上下文分层）：
1. 每次请求时，通过 WorkspacePromptLoader 动态加载 workspace/*.md
2. 将 system_prompt + user_message 发送给模型
3. 返回模型的回复

包含：记忆存储（SessionMemoryManager + DailyMemoryWriter）
"""
from datetime import datetime, timezone
from typing import Optional, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from app.graph.sys_prompt_builder import get_supervisor_loader
from app.services.model import get_model_router
from app.services.memory import (
    get_session_memory_manager,
    get_daily_log_manager,
    get_memory_injector,
)


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
        self._memory_manager = get_session_memory_manager()
        self._daily_writer = get_daily_log_manager()
        self._injector = get_memory_injector()

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

        # 2. 加载会话记忆（今日 + 昨日 + MEMORY.md）
        session_memory = await self._injector.load_session_memory(
            user_id=user_id,
            session_id=session_id,
            mode="main",
        )

        # 3. 获取对话历史并格式化
        mem = self._memory_manager.get_memory(session_id)
        history = mem.get_history()
        formatted_history = self._format_history(history)

        # 4. 将 history 追加到 system prompt
        if session_memory:
            memory_section = f"\n\n## Memory\n\n{session_memory}"
        else:
            memory_section = ""
        if formatted_history:
            full_system = f"{system_prompt}{memory_section}\n\n## 对话历史\n{formatted_history}"
        else:
            full_system = f"{system_prompt}{memory_section}"

        # 4. 将 full_system + user_message 发送给模型（带工具调用）
        model_used = self._detect_model()

        # 构建消息列表
        chat_messages = []
        if full_system:
            chat_messages.append({"role": "system", "content": full_system})
        chat_messages.append({"role": "user", "content": message})

        # 使用 Tool Calling
        answer = await self._router.call_with_tools(
            messages=chat_messages,
            system="",
        )

        # 5. 保存对话到记忆（history_count 是保存前的消息数）
        history_count = len(history)
        mem.save_context({"input": message}, {"output": answer})
        self._daily_writer.append(
            session_id=session_id,
            user_id=user_id,
            human_message=message,
            ai_message=answer,
        )

        return {
            "answer": answer,
            "metadata": {
                "model": model_used,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "reasoning": None,  # 预留扩展
        }

    async def chat_stream(
        self,
        user_id: str,
        session_id: str,
        message: str,
    ) -> None:
        """处理流式对话请求（后台任务）。

        替代 chat() 方法，将事件通过 StreamManager 发射。
        """
        from app.services.streaming import StreamCallbackHandler, get_stream_manager

        stream_manager = await get_stream_manager()
        callback = StreamCallbackHandler(stream_manager, session_id)

        # PlanningAgent.plan() handles system prompt, memory, and messages internally
        mem = self._memory_manager.get_memory(session_id)

        # 调用 PlanningAgent（带 streaming）
        try:
            from app.agents.supervisor import PlanningAgent

            supervisor = PlanningAgent()
            result = await supervisor.plan(
                user_id=user_id,
                session_id=session_id,
                message=message,
                stream_callback=callback,
            )

            # PlanningAgent.plan() 返回包含 answer 字段的 dict
            answer = result.get("answer", "抱歉，生成回复失败。")

            # 发射最终回复
            await callback.on_final(answer)

            # 保存到记忆
            mem.save_context({"input": message}, {"output": answer})
            self._daily_writer.append(
                session_id=session_id,
                user_id=user_id,
                human_message=message,
                ai_message=answer,
            )

        except Exception as e:
            await callback.on_error(str(e), recoverable=False)

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
