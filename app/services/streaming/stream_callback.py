"""app/services/streaming/stream_callback.py - LangChain 风格回调处理器。

实现以下方法：
- on_llm_start: 发射 llm_start 事件
- on_llm_new_token: 发射 llm_new_token 事件（用于打字机效果）
- on_llm_end: 发射 llm_end + token_usage 事件
- on_tool_start: 发射 tool_start 事件
- on_tool_end: 发射 tool_end 事件（结果截取为摘要）
- on_reasoning_step: 发射 reasoning_step 事件（LLM 思考过程）
- on_iteration: 发射 iteration 事件（工具调用循环次数）
"""
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from langchain_core.callbacks import AsyncCallbackHandler

if TYPE_CHECKING:
    from app.services.streaming.stream_manager import StreamManager

DEEPSEEK_PRICE_PER_1K_TOKENS = 0.001  # per 1K tokens


class StreamCallbackHandler:
    """LangChain 风格回调处理器。

    通过 __init__ 注入 StreamManager 实例和 session_id。
    """

    def __init__(self, stream_manager: "StreamManager", session_id: str):
        self._stream_manager = stream_manager
        self._session_id = session_id

    async def on_llm_start(self, model: str) -> None:
        """LLM 开始推理。"""
        await self._stream_manager.emit(
            self._session_id,
            "llm_start",
            {"model": model}
        )

    async def on_llm_new_token(self, token: str) -> None:
        """每个新 token（用于打字机效果）。"""
        await self._stream_manager.emit(
            self._session_id,
            "llm_new_token",
            {"token": token}
        )

    async def on_llm_end(
        self,
        total_tokens: int,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        """LLM 生成完成。"""
        # 计算成本 (DeepSeek 近似单价)
        cost_per_token = DEEPSEEK_PRICE_PER_1K_TOKENS / 1000
        cost_usd = total_tokens * cost_per_token

        await self._stream_manager.emit(
            self._session_id,
            "llm_end",
            {
                "total_tokens": total_tokens,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost_usd": round(cost_usd, 6),
            }
        )

    async def on_tool_start(
        self,
        tool: str,
        tool_call_id: str,
    ) -> None:
        """工具开始调用。"""
        await self._stream_manager.tool_start(
            self._session_id,
            tool,
            tool_call_id,
        )

    async def on_tool_end(
        self,
        tool: str,
        tool_result: Any,
        duration_ms: int,
    ) -> None:
        """工具调用完成。

        将完整结果截取为摘要。
        """
        summary = self._summarize_result(tool_result)
        await self._stream_manager.tool_end(
            self._session_id,
            tool,
            summary,
            duration_ms,
        )

    async def on_tool_error(
        self,
        tool: str,
        error: str,
    ) -> None:
        """工具执行失败。"""
        await self._stream_manager.tool_error(
            self._session_id,
            tool,
            error,
        )

    async def on_reasoning_step(self, step: str) -> None:
        """发射 LLM 推理步骤。"""
        await self._stream_manager.reasoning_step(
            self._session_id,
            step,
        )

    async def on_iteration(self, iteration: int, max_iterations: int) -> None:
        """发射工具调用循环次数。"""
        await self._stream_manager.iteration(
            self._session_id,
            iteration,
            max_iterations,
        )

    async def on_agent_switch(self, agent: str) -> None:
        """Agent 切换。"""
        await self._stream_manager.agent_switch(self._session_id, agent)

    async def on_phase_start(self, phase: str, description: str = "") -> None:
        """Agent 阶段开始，发射 agent_switch 事件。"""
        await self._stream_manager.agent_switch(self._session_id, phase, description)

    async def on_skill_start(self, skill: str, tool_call_id: str) -> None:
        """Skill/Tool 开始调用，发射 skill_start 事件。"""
        await self._stream_manager.skill_start(self._session_id, skill, tool_call_id)

    async def on_skill_end(
        self,
        skill: str,
        summary: Any,
        duration_ms: int,
    ) -> None:
        """Skill/Tool 结束，发射 skill_end 事件。"""
        await self._stream_manager.skill_end(self._session_id, skill, summary, duration_ms)

    async def on_model_switch(self, model: str, reason: str) -> None:
        """模型切换。"""
        await self._stream_manager.model_switch(
            self._session_id,
            model,
            reason,
        )

    async def on_error(self, error: str, recoverable: bool = True) -> None:
        """错误。"""
        await self._stream_manager.error(
            self._session_id,
            error,
        )

    async def on_final(self, answer: str) -> None:
        """最终回复。"""
        await self._stream_manager.final(self._session_id, answer)

    def _summarize_result(self, result: Any, max_length: int = 100) -> str:
        """将工具结果截取为摘要。

        避免 SSE 传输过大数据。
        """
        if result is None:
            return "无结果"

        if isinstance(result, str):
            summary = result
        elif isinstance(result, dict):
            # 提取关键字段作为摘要
            if "items" in result and isinstance(result["items"], list):
                summary = f"找到 {len(result['items'])} 个结果"
            elif "budget" in result:
                summary = f"预算 ¥{result.get('budget', 'N/A')}"
            elif "total" in result:
                summary = f"总计 ¥{result.get('total', 'N/A')}"
            else:
                summary = str(result)[:max_length]
        elif isinstance(result, list):
            summary = f"共 {len(result)} 项"
        else:
            summary = str(result)[:max_length]

        if len(summary) > max_length:
            summary = summary[:max_length] + "..."

        return summary


class StreamCallbackHandlerAdapter:
    """将旧的 StreamCallbackHandler 适配为 LangChain callback。

    用于兼容旧的 non-LangChain 代码路径。
    """

    def __init__(self, stream_callback: Optional["StreamCallbackHandler"]):
        self._cb = stream_callback

    async def on_llm_start(self, model: str):
        if self._cb:
            await self._cb.on_llm_start(model)

    async def on_llm_new_token(self, token: str):
        if self._cb:
            await self._cb.on_llm_new_token(token)

    async def on_llm_end(self, total_tokens: int, prompt_tokens: int, completion_tokens: int):
        if self._cb:
            await self._cb.on_llm_end(total_tokens, prompt_tokens, completion_tokens)

    async def on_tool_start(self, tool: str, tool_call_id: str):
        if self._cb:
            await self._cb.on_tool_start(tool, tool_call_id)

    async def on_tool_end(self, tool: str, tool_result: Any, duration_ms: int):
        if self._cb:
            await self._cb.on_tool_end(tool, tool_result, duration_ms)


class LangChainStreamCallbackHandler(AsyncCallbackHandler):
    """LangChain 兼容的流式回调处理器。

    将 LangChain 的 callback 事件转换为 StreamCallbackHandler 事件。
    用于 ModelRouter 的 streaming 调用。
    """

    def __init__(self, stream_callback: "StreamCallbackHandler"):
        self._cb = stream_callback
        self._model_name = "deepseek"

    async def on_chat_model_start(
        self,
        serialized,
        messages,
        *,
        run_id,
        parent_run_id=None,
        **kwargs,
    ):
        """LLM 开始推理。"""
        # 从 serialized 获取模型名称
        model_name = "deepseek"
        if serialized and hasattr(serialized, "get"):
            model_id = serialized.get("id", [])
            if model_id and len(model_id) > 0:
                model_name = model_id[-1]

        self._model_name = model_name
        await self._cb.on_llm_start(model_name)
        # 发射 agent_switch
        await self._cb.on_phase_start("LLM 推理", f"使用 {model_name} 模型")

    async def on_llm_new_token(
        self,
        token: str,
        *,
        run_id,
        parent_run_id=None,
        **kwargs,
    ):
        """每个新 token。"""
        await self._cb.on_llm_new_token(token)

    async def on_llm_end(
        self,
        response,
        *,
        run_id,
        parent_run_id=None,
        **kwargs,
    ):
        """LLM 生成完成。"""
        # 尝试从 response 获取 token usage
        total_tokens = 0
        prompt_tokens = 0
        completion_tokens = 0

        # LangChain 在流式结束时可能没有 usage_metadata
        # 尝试从 llm_output 获取
        if hasattr(response, "llm_output") and response.llm_output:
            usage = response.llm_output.get("token_usage", {})
            if usage:
                total_tokens = usage.get("total_tokens", 0)
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)

        await self._cb.on_llm_end(total_tokens, prompt_tokens, completion_tokens)
