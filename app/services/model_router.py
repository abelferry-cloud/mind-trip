# app/services/model_router.py
"""模型路由 - 处理模型回退链（OpenAI → Claude → 本地）。

根据设计文档第 6.1 节：
- 429: 等待 5 秒后重试主模型，如果仍然 429 则切换
- 500: 立即切换
- 超时：立即切换
- 每请求粒度

支持 Tool Calling（OpenAI 兼容协议）。
"""
import asyncio
from typing import Any, Dict, List, Literal, Optional
from app.config import get_settings
from app.services.tool_registry import get_tools_schema
from app.services.tool_calling_service import get_tool_calling_service

ModelName = Literal["openai", "claude", "local"]


class ModelRouter:
    def __init__(self):
        self.settings = get_settings()
        self._primary_available = True  # optimistic

    def is_primary_available(self) -> bool:
        return self._primary_available

    async def call(self, prompt: str, system: str = "") -> str:
        """按链式顺序调用模型，失败时切换（无工具调用）。

        引发：
            Exception: 如果链中所有模型都失败
        """
        chain = self.settings.model_chain_list
        last_error = None

        for model in chain:
            try:
                if model == "openai":
                    return await self._call_openai(prompt, system)
                elif model == "claude":
                    return await self._call_claude(prompt, system)
                elif model == "local":
                    return await self._call_local(prompt, system)
            except Exception as e:
                last_error = e
                if self._is_retryable(e):
                    if "429" in str(e):
                        await asyncio.sleep(5)
                        continue  # retry same model
                else:
                    continue  # switch to next model

        # 全部失败
        raise Exception(f"所有模型都失败。最后错误：{last_error}")

    async def call_with_tools(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        stream_callback: Optional[Any] = None,
    ) -> str:
        """带工具调用的模型调用（OpenAI Tool Calling 协议）。

        按链式顺序调用，失败时切换。

        Args:
            messages: 消息列表（会直接修改）
            system: 系统提示词
            stream_callback: 可选的流式回调处理器

        Returns:
            LLM 的最终回答文本
        """
        chain = self.settings.model_chain_list
        last_error = None

        for model in chain:
            try:
                if model == "openai":
                    return await self._call_openai_with_tools(messages, system, stream_callback)
                elif model == "claude":
                    return await self._call_claude_with_tools(messages, system)
                elif model == "local":
                    return await self._call_local_with_tools(messages, system)
            except Exception as e:
                last_error = e
                if self._is_retryable(e):
                    if "429" in str(e):
                        await asyncio.sleep(5)
                        continue  # retry same model
                else:
                    continue  # switch to next model

        # 全部失败
        raise Exception(f"所有模型都失败。最后错误：{last_error}")

    def _is_retryable(self, error: Exception) -> bool:
        err_str = str(error)
        # 根据设计文档第 6.1 节：
        # - 429 速率限制：等待后重试（不跳过到下一个模型）
        # - 500 服务器错误：立即跳过到下一个模型
        # - 超时：立即跳过到下一个模型
        if "429" in err_str:
            return True  # 等待后重试同一模型
        return False  # 所有其他错误 → 切换到下一个模型

    async def _call_openai(self, prompt: str, system: str) -> str:
        """通过 LangChain 调用 DeepSeek API（OpenAI 兼容）。

        使用 OpenAI 兼容端点调用 DeepSeek API。
        """
        if not self.settings.deepseek_api_key:
            raise Exception("DEEPSEEK_API_KEY not set")

        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise Exception("openai package not installed")

        client = AsyncOpenAI(
            api_key=self.settings.deepseek_api_key,
            base_url=self.settings.deepseek_base_url
        )

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=self.settings.deepseek_model,
            messages=messages
        )

        self._primary_available = True
        return response.choices[0].message.content

    async def _call_claude(self, prompt: str, system: str) -> str:
        if not self.settings.claude_api_key:
            raise Exception("CLAUDE_API_KEY not set")
        await asyncio.sleep(0.01)
        return f"[Claude] {prompt[:50]}..."

    async def _call_local(self, prompt: str, system: str) -> str:
        # 本地模型占位符（如 ollama）
        return f"[Local] {prompt[:50]}..."

    # ==================== Tool Calling Methods ====================

    async def _call_openai_with_tools(
        self,
        messages: List[Dict[str, Any]],
        system: str,
        stream_callback: Optional[Any] = None,
    ) -> str:
        """使用 Tool Calling 调用 OpenAI 兼容 API with optional streaming."""
        if not self.settings.deepseek_api_key:
            raise Exception("DEEPSEEK_API_KEY not set")

        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=self.settings.deepseek_api_key,
            base_url=self.settings.deepseek_base_url,
        )

        # 如果第一条消息是 system，就保持不变
        # 否则在开头插入 system 消息
        if not messages or messages[0].get("role") != "system":
            if system:
                messages.insert(0, {"role": "system", "content": system})

        tools = get_tools_schema()

        # Emit llm_start
        if stream_callback:
            await stream_callback.on_llm_start(self.settings.deepseek_model)

        # Use streaming if callback provided
        if stream_callback:
            return await self._call_openai_with_tools_streaming(
                client, messages, tools, stream_callback
            )
        else:
            # Non-streaming (existing behavior via ToolCallingService)
            tc_service = get_tool_calling_service()
            result = await tc_service.call_with_tools(
                messages=messages,
                tools=tools,
                model="openai",
            )
            self._primary_available = True
            return result

    async def _call_openai_with_tools_streaming(
        self,
        client,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        stream_callback,
    ) -> str:
        """Streaming path for OpenAI tool calling."""
        # Use streaming for content only, handle tool_calls from final chunk
        request_params = {
            "model": self.settings.deepseek_model,
            "messages": messages,
        }
        if tools:
            request_params["tools"] = tools
            request_params["tool_choice"] = "auto"
        request_params["stream"] = True

        response = await client.chat.completions.create(**request_params)

        accumulated_content = ""
        final_chunk = None  # Keep last chunk to check for tool_calls

        async for chunk in response:
            final_chunk = chunk
            if chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                accumulated_content += token
                await stream_callback.on_llm_new_token(token)

        # After streaming, parse tool_calls from final chunk
        tool_calls = None
        if final_chunk and hasattr(final_chunk.choices[0], 'message') and final_chunk.choices[0].message.tool_calls:
            tool_calls = [
                {"id": tc.id, "type": tc.type, "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in final_chunk.choices[0].message.tool_calls
            ]

        assistant_msg = {
            "role": "assistant",
            "content": accumulated_content,
        }
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls

        messages.append(assistant_msg)

        # If there are tool_calls, execute them via ToolCallingService
        if tool_calls:
            return await self._execute_tool_calls_with_callback(
                messages, self.settings.deepseek_model, stream_callback
            )

        # Emit llm_end with token counts (from usage if available)
        usage = getattr(response, 'usage', None) or {}
        if stream_callback:
            await stream_callback.on_llm_end(
                total_tokens=usage.get('total_tokens', 0),
                prompt_tokens=usage.get('prompt_tokens', 0),
                completion_tokens=usage.get('completion_tokens', 0),
            )

        self._primary_available = True
        return accumulated_content

    async def _execute_tool_calls_with_callback(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        stream_callback,
    ) -> str:
        """Execute tool calls via ToolCallingService with streaming callback."""
        tc_service = get_tool_calling_service()
        # Pass stream_callback to ToolCallingService
        return await tc_service.call_with_tools(
            messages=messages,
            tools=get_tools_schema(),
            model=model,
            stream_callback=stream_callback,
        )

    async def _call_claude_with_tools(
        self,
        messages: List[Dict[str, Any]],
        system: str,
    ) -> str:
        """Claude Tool Calling（预留）。"""
        if not self.settings.claude_api_key:
            raise Exception("CLAUDE_API_KEY not set")
        await asyncio.sleep(0.01)
        return "[Claude] Tool calling not yet implemented."

    async def _call_local_with_tools(
        self,
        messages: List[Dict[str, Any]],
        system: str,
    ) -> str:
        """本地模型 Tool Calling（预留）。"""
        return "[Local] Tool calling not yet implemented for local models."


_router: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
