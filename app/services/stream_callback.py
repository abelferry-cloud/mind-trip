"""app/services/stream_callback.py - LangChain 风格回调处理器。

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
from typing import Any, Optional


class StreamCallbackHandler:
    """LangChain 风格回调处理器。

    通过 __init__ 注入 StreamManager 实例和 session_id。
    """

    def __init__(self, stream_manager, session_id: str):
        self._stream_manager = stream_manager
        self._session_id = session_id
        self._iteration = 0
        self._max_iterations = 10

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
        cost_per_token = 0.001 / 1000  # $0.001 per 1K tokens
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

    async def on_iteration(self, iteration: int) -> None:
        """发射工具调用循环次数。"""
        self._iteration = iteration
        await self._stream_manager.iteration(
            self._session_id,
            iteration,
            self._max_iterations,
        )

    async def on_agent_switch(self, agent: str) -> None:
        """Agent 切换。"""
        await self._stream_manager.agent_switch(self._session_id, agent)

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
