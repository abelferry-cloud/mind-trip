"""LangChain 风格回调处理器 - 适配 StreamManager.

实现 langchain_core.callbacks.AsyncCallbackHandler 接口，
将 LangChain 事件转换为 SSE 事件.
"""
import time
from typing import TYPE_CHECKING, Any, Dict, Optional
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import Generation, LLMResult

if TYPE_CHECKING:
    from app.services.streaming.stream_callback import StreamCallbackHandler

DEEPSEEK_PRICE_PER_1K_TOKENS = 0.001  # per 1K tokens


class LangChainCallbackHandler(AsyncCallbackHandler):
    """LangChain 风格回调处理器.

    将 LangChain 的事件（on_chat_model_start, on_llm_new_token 等）
    转换为 SSE 事件并通过 StreamCallbackHandler 发射.
    """

    def __init__(self, stream_callback: "StreamCallbackHandler", session_id: str = "default"):
        self._stream_callback = stream_callback
        self._session_id = session_id
        self._current_agent = "PlanningAgent"
        self._current_tool = "unknown"
        self._tool_start_time: Dict[str, float] = {}
        self._token_buffer = ""
        self._last_token_time = time.time()

    async def on_chat_model_start(
        self,
        serialized,
        messages,
        *,
        run_id,
        parent_run_id=None,
        **kwargs,
    ):
        """LLM 开始推理，发射 agent_switch + llm_start."""
        model_name = serialized.get("id", ["unknown"])[-1] if serialized else "unknown"
        # 发射 agent_switch
        if hasattr(self._stream_callback, "on_agent_switch"):
            await self._stream_callback.on_agent_switch(self._current_agent)
        # 发射 llm_start
        if hasattr(self._stream_callback, "on_llm_start"):
            await self._stream_callback.on_llm_start(model_name)
        # 发射 reasoning_start
        if hasattr(self._stream_callback, "on_reasoning_step"):
            await self._stream_callback.on_reasoning_step("LLM 开始推理...")

    async def on_llm_new_token(
        self,
        token: str,
        *,
        run_id,
        parent_run_id=None,
        **kwargs,
    ):
        """每个新 token，发射 llm_new_token."""
        self._token_buffer += token
        self._last_token_time = time.time()
        if hasattr(self._stream_callback, "on_llm_new_token"):
            await self._stream_callback.on_llm_new_token(token)

    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id,
        parent_run_id=None,
        **kwargs,
    ):
        """LLM 生成完成，发射 llm_end + token_usage."""
        # 从 response 获取 token usage
        # LangChain 的 LLMResult 在 streaming 时可能没有完整usage
        total, prompt, completion = 0, 0, 0

        # 尝试从 response 提取 usage
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = response.usage_metadata
            total = usage.get("total_tokens", 0)
            prompt = usage.get("input_tokens", 0)
            completion = usage.get("output_tokens", 0)
        elif hasattr(response, "llm_output") and response.llm_output:
            # 尝试从 llm_output 获取
            llm_output = response.llm_output
            if isinstance(llm_output, dict):
                usage = llm_output.get("token_usage", {})
                if usage:
                    total = usage.get("total_tokens", 0)
                    prompt = usage.get("prompt_tokens", 0)
                    completion = usage.get("completion_tokens", 0)

        cost_usd = total * DEEPSEEK_PRICE_PER_1K_TOKENS / 1000

        if hasattr(self._stream_callback, "on_llm_end"):
            await self._stream_callback.on_llm_end(
                total_tokens=total,
                prompt_tokens=prompt,
                completion_tokens=completion,
            )

    async def on_tool_start(
        self,
        serialized,
        input_str: str,
        *,
        run_id,
        parent_run_id=None,
        **kwargs,
    ):
        """工具开始调用，发射 tool_start."""
        tool_name = serialized.get("name", "unknown") if serialized else "unknown"
        self._current_tool = tool_name
        self._tool_start_time[run_id] = time.time()

        if hasattr(self._stream_callback, "on_tool_start"):
            await self._stream_callback.on_tool_start(
                tool=tool_name,
                tool_call_id=str(run_id),
            )

    async def on_tool_end(
        self,
        output: str,
        *,
        run_id,
        parent_run_id=None,
        **kwargs,
    ):
        """工具调用完成，发射 tool_end."""
        # 从 run_id 获取 tool_name 和耗时
        start_time = self._tool_start_time.pop(run_id, None)
        duration_ms = int((time.time() - start_time) * 1000) if start_time else 0

        summary = self._summarize_output(output)
        if hasattr(self._stream_callback, "on_tool_end"):
            await self._stream_callback.on_tool_end(
                tool=self._current_tool,
                tool_result=summary,
                duration_ms=duration_ms,
            )

    async def on_tool_error(
        self,
        error: Exception,
        *,
        run_id,
        parent_run_id=None,
        **kwargs,
    ):
        """工具执行失败，发射 tool_error."""
        if hasattr(self._stream_callback, "on_tool_error"):
            await self._stream_callback.on_tool_error(
                tool=self._current_tool,
                error=str(error),
            )

    def _summarize_output(self, output: Any, max_length: int = 100) -> str:
        """将工具输出截取为摘要."""
        if output is None:
            return "无结果"
        if isinstance(output, str):
            summary = output
        elif isinstance(output, dict):
            if "items" in output and isinstance(output["items"], list):
                summary = f"找到 {len(output['items'])} 个结果"
            elif "budget" in output:
                summary = f"预算 ¥{output.get('budget', 'N/A')}"
            else:
                summary = str(output)[:max_length]
        elif isinstance(output, list):
            summary = f"共 {len(output)} 项"
        else:
            summary = str(output)[:max_length]

        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        return summary
