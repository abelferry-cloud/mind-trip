"""app/services/tool_calling_service.py - Tool Calling 服务。

遵循 OpenClaw 的 OpenAI Tool Calling 协议：
1. 发送消息 + tools 声明到 LLM
2. 如果 LLM 返回 tool_calls，执行工具并追加结果
3. 重复直到 LLM 返回最终回答
"""
import asyncio
import json
import structlog
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.services.tool_registry import get_tool

logger = structlog.get_logger()


class ToolCallingService:
    """处理 Tool Calling 循环的服务。"""

    def __init__(self):
        self.settings = get_settings()
        self._max_iterations = 10  # 防止无限循环

    async def call_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        model: str = "openai",
        stream_callback: Optional[Any] = None,
    ) -> str:
        """带工具调用地调用模型。

        遵循 OpenClaw 模式：
        - 工具调用是"静默"的后台操作
        - 用户的直接回复立即返回，不等待工具执行
        - 工具执行结果追加到上下文，但不显示给用户

        Args:
            messages: 消息列表（会直接修改，追加 tool 结果）
            tools: 工具声明数组
            model: 使用的模型类型
            stream_callback: 可选的流式回调处理器

        Returns:
            LLM 的最终回答文本（用于直接回复用户）
        """
        iteration = 0
        side_content = None

        while iteration < self._max_iterations:
            iteration += 1

            # 发射迭代开始事件
            if stream_callback:
                await stream_callback.on_iteration(iteration, self._max_iterations)

            # 调用 LLM
            response_data = await self._call_llm(messages, tools, model)

            # 检查是否有 tool_calls
            tool_calls = response_data.get("tool_calls", [])
            content = response_data.get("content", "")

            if not tool_calls:
                # 没有工具调用，content 即为最终回答
                return content

            # 有工具调用时：
            # 1. 如果同时有 content（LLM 的"副作用"回复），记录下来
            # 2. 执行所有工具
            # 3. 继续循环，LLM 会生成真正的最终回复
            # 4. 如果最终回复仍是工具调用（不应该），用记录的 content 作为后备

            side_content = content if content else None

            # 执行工具调用
            for tool_call in tool_calls:
                if stream_callback:
                    await stream_callback.on_tool_start(
                        tool_call["function"]["name"],
                        tool_call["id"]
                    )
                tool_result = await self._execute_tool_call(tool_call, stream_callback)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(tool_result, ensure_ascii=False),
                })

            # 继续循环让 LLM 生成最终回复

        # 达到最大迭代次数
        # 如果有记录的 side_content，用它作为后备
        if side_content:
            return side_content

        logger.warning("tool_calling_max_iterations_reached")
        return "抱歉，工具调用超出最大次数限制。请稍后重试。"

    async def _call_llm(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        model: str,
    ) -> Dict[str, Any]:
        """调用 LLM，返回 assistant 消息（可能包含 tool_calls）。"""
        if model == "openai":
            return await self._call_openai(messages, tools)
        elif model == "claude":
            return await self._call_claude(messages, tools)
        else:
            return await self._call_local(messages, tools)

    async def _call_openai(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """通过 OpenAI 兼容 API 调用。

        Returns:
            assistant 消息 dict，可能包含 tool_calls
        """
        if not self.settings.deepseek_api_key:
            raise Exception("DEEPSEEK_API_KEY not set")

        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=self.settings.deepseek_api_key,
            base_url=self.settings.deepseek_base_url,
        )

        # 构造请求参数
        request_params = {
            "model": self.settings.deepseek_model,
            "messages": messages,
        }

        # 只有当有工具时才传 tools 参数
        if tools:
            request_params["tools"] = tools
            request_params["tool_choice"] = "auto"

        response = await client.chat.completions.create(**request_params)

        msg = response.choices[0].message

        # 构造 assistant 消息
        assistant_msg = {
            "role": "assistant",
            "content": msg.content or "",
        }

        # 如果有 tool_calls，添加到消息中
        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                }
                for tc in msg.tool_calls
            ]

        # 追加到 messages
        messages.append(assistant_msg)

        return assistant_msg

    async def _call_claude(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Claude API 调用（预留）。"""
        if not self.settings.claude_api_key:
            raise Exception("CLAUDE_API_KEY not set")
        await asyncio.sleep(0.01)
        return {
            "role": "assistant",
            "content": "[Claude] Tool calling not yet implemented for Claude.",
            "tool_calls": [],
        }

    async def _call_local(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """本地模型调用（预留）。"""
        return {
            "role": "assistant",
            "content": "[Local] Tool calling not yet implemented for local models.",
            "tool_calls": [],
        }

    async def _execute_tool_call(
        self,
        tool_call: Dict[str, Any],
        stream_callback: Optional[Any] = None,
    ) -> Any:
        """执行单个工具调用。

        Args:
            tool_call: {
                "id": "call_xxx",
                "type": "function",
                "function": {
                    "name": "tool_name",
                    "arguments": '{"arg1": "value1", ...}'
                }
            }
            stream_callback: 可选的流式回调处理器

        Returns:
            工具执行结果
        """
        import time
        func_name = tool_call["function"]["name"]
        func_args = tool_call["function"]["arguments"]

        tool = get_tool(func_name)
        if not tool:
            logger.error("tool_not_found", tool_name=func_name)
            if stream_callback:
                await stream_callback.on_tool_error(func_name, f"Tool '{func_name}' not found")
            return {"success": False, "error": f"Tool '{func_name}' not found"}

        start_time = time.time()
        try:
            # 解析参数（arguments 是 JSON 字符串）
            if isinstance(func_args, str):
                args_dict = json.loads(func_args)
            else:
                args_dict = func_args

            # 调用工具函数
            result = tool.func.invoke(args_dict)

            # 如果是协程，等待完成
            if asyncio.iscoroutine(result):
                result = await result

            # 转为 dict（如果是 Pydantic 模型）
            if hasattr(result, "model_dump"):
                result = result.model_dump()
            elif hasattr(result, "dict"):
                result = result.dict()

            # 计算执行时间并通知回调
            duration_ms = int((time.time() - start_time) * 1000)
            if stream_callback:
                await stream_callback.on_tool_end(func_name, result, duration_ms)

            return result

        except Exception as e:
            logger.error("tool_execution_failed", tool_name=func_name, error=str(e))
            if stream_callback:
                await stream_callback.on_tool_error(func_name, str(e))
            return {"success": False, "error": str(e)}


# 全局实例
_tool_calling_service: Optional[ToolCallingService] = None


def get_tool_calling_service() -> ToolCallingService:
    global _tool_calling_service
    if _tool_calling_service is None:
        _tool_calling_service = ToolCallingService()
    return _tool_calling_service
