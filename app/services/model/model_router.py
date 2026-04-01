# app/services/model/model_router.py
"""模型路由 - LangChain Runnable 抽象层.

使用 LangChain ChatOpenAI (OpenAI 兼容) + fallback 链.
支持 DeepSeek, OpenAI, Claude, Local 模型.
正确使用 bind_tools() 实现工具调用.
"""
import asyncio
import json
import time
from typing import Any, Dict, List, Literal, Optional

from app.config import get_settings
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage

ModelName = Literal["deepseek", "openai", "claude", "local"]

# DeepSeek 价格（per 1K tokens）
DEEPSEEK_PRICE_PER_1K_TOKENS = 0.001


class ModelRouter:
    """模型路由器 - LangChain Runnable 风格.

    使用 ChatOpenAI (OpenAI 兼容) 实现 DeepSeek 调用,
    通过 bind_tools() 实现真正的工具调用.
    """

    def __init__(self):
        self.settings = get_settings()
        self._clients: Dict[str, ChatOpenAI] = {}
        self._setup_clients()

    def _setup_clients(self):
        """初始化各模型的 ChatOpenAI 客户端."""
        # DeepSeek (主模型)
        if self.settings.deepseek_api_key:
            self._clients["deepseek"] = ChatOpenAI(
                model=self.settings.deepseek_model or "deepseek-chat",
                api_key=self.settings.deepseek_api_key,
                base_url=self.settings.deepseek_base_url,
                streaming=True,
                temperature=0.7,
                max_tokens=4000,
            )

        # OpenAI (fallback)
        if self.settings.openai_api_key:
            self._clients["openai"] = ChatOpenAI(
                model=self.settings.openai_model or "gpt-4o-mini",
                api_key=self.settings.openai_api_key,
                streaming=True,
                temperature=0.7,
            )

    def _get_primary_model(self) -> ChatOpenAI:
        """获取主模型（DeepSeek 或 OpenAI）."""
        primary = self._clients.get("deepseek") or self._clients.get("openai")
        if not primary:
            raise Exception("No model client available")
        return primary

    async def call_with_tools(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        stream_callback: Optional[Any] = None,
    ) -> str:
        """带工具调用的模型调用（LangChain bind_tools 风格）.

        Args:
            messages: 消息列表
            system: 系统提示词
            stream_callback: 流式回调处理器

        Returns:
            LLM 的最终回答文本
        """
        # 转换消息格式
        lc_messages = self._convert_messages(messages, system)

        # 获取工具 schema
        from app.services.tools.tool_registry import get_tools_schema
        tools = get_tools_schema()

        # 获取主模型
        primary = self._get_primary_model()

        # 如果有工具，绑定工具并进入工具调用循环
        if tools:
            return await self._call_with_tools_streaming(
                primary, lc_messages, tools, stream_callback
            )
        else:
            return await self._call_streaming(primary, lc_messages, stream_callback)

    async def _call_streaming(
        self,
        model: ChatOpenAI,
        messages: List[Any],
        stream_callback: Optional[Any] = None,
    ) -> str:
        """流式调用模型，通过 LangChain callback system."""
        accumulated = ""

        # 构建 config，通过 LangChain callback system 传递
        config = {}
        if stream_callback:
            from app.services.streaming.langchain_callback import LangChainCallbackHandler
            handler = LangChainCallbackHandler(stream_callback, session_id="default")
            config["callbacks"] = [handler]

        async for chunk in model.astream(messages, config):
            if chunk.content:
                accumulated += chunk.content
                if stream_callback:
                    await stream_callback.on_llm_new_token(chunk.content)

        return accumulated

    async def _call_with_tools_streaming(
        self,
        model: ChatOpenAI,
        messages: List[Any],
        tools: List[Dict[str, Any]],
        stream_callback: Optional[Any] = None,
    ) -> str:
        """带工具调用的流式模型调用.

        使用 bind_tools() 绑定工具，并通过工具调用循环处理.
        正确处理流式响应中的 tool_calls（可能在多个 chunk 中累积）.
        """
        from app.services.tools.tool_registry import get_tool

        # 绑定工具
        model_with_tools = model.bind_tools(tools, tool_choice="auto")

        accumulated = ""
        iteration = 0
        max_iterations = 10

        while iteration < max_iterations:
            iteration += 1

            # 发射迭代开始事件
            if stream_callback:
                await stream_callback.on_iteration(iteration, max_iterations)

            # 构建 config
            config = {}
            if stream_callback:
                from app.services.streaming.langchain_callback import LangChainCallbackHandler
                handler = LangChainCallbackHandler(stream_callback, session_id="default")
                config["callbacks"] = [handler]

            # 流式调用模型，收集完整的 AIMessage
            # LangChain 流式返回的是部分消息，需要累积
            response_content = ""
            response_tool_calls = []
            tool_call_map = {}  # id -> tool_call

            async for chunk in model_with_tools.astream(messages, config):
                # 处理内容 token
                if hasattr(chunk, "content") and chunk.content:
                    response_content += chunk.content
                    accumulated += chunk.content
                    if stream_callback:
                        await stream_callback.on_llm_new_token(chunk.content)

                # 处理 tool_calls（可能在多个 chunk 中）
                if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                    for tc in chunk.tool_calls:
                        # 使用 id 作为唯一标识
                        if tc.id not in tool_call_map:
                            response_tool_calls.append(tc)
                            tool_call_map[tc.id] = tc

            # 检查是否有工具调用需要处理
            if response_tool_calls:
                # 先添加助手消息（包含 tool_calls）
                assistant_msg = AIMessage(content=response_content)
                # 手动设置 tool_calls（因为 AIMessage 可能不支持直接设置）
                if hasattr(assistant_msg, 'tool_calls'):
                    assistant_msg.tool_calls = response_tool_calls
                messages.append(assistant_msg)

                # 执行所有工具调用
                for tool_call in response_tool_calls:
                    # 发射工具开始事件
                    if stream_callback:
                        await stream_callback.on_tool_start(
                            tool_call.name,
                            tool_call.id,
                        )

                    # 执行工具
                    tool_result = await self._execute_tool(
                        tool_call,
                        stream_callback,
                    )

                    # 将工具结果追加到消息
                    messages.append(
                        ToolMessage(
                            tool_call_id=tool_call.id,
                            content=json.dumps(tool_result, ensure_ascii=False),
                        )
                    )

                # 继续循环，让 LLM 处理工具结果
                continue

            # 没有工具调用，检查是否有内容
            if response_content:
                # 添加助手消息到上下文
                messages.append(AIMessage(content=response_content))
                # 这是最终回复
                return accumulated

            # 没有内容也没有工具调用，可能是第一次调用就要求工具
            # 继续循环

        return accumulated

    async def _execute_tool(
        self,
        tool_call: Any,
        stream_callback: Optional[Any] = None,
    ) -> Any:
        """执行单个工具调用.

        Args:
            tool_call: LangChain 的 ToolCall 对象
            stream_callback: 流式回调

        Returns:
            工具执行结果
        """
        from app.services.tools.tool_registry import get_tool

        start_time = time.time()
        func_name = tool_call.name

        # 解析参数
        try:
            if hasattr(tool_call, "args"):
                args_dict = tool_call.args
            elif hasattr(tool_call, "arguments"):
                if isinstance(tool_call.arguments, str):
                    args_dict = json.loads(tool_call.arguments)
                else:
                    args_dict = tool_call.arguments
            else:
                args_dict = {}
        except json.JSONDecodeError:
            args_dict = {}

        tool = get_tool(func_name)
        if not tool:
            error_result = {"success": False, "error": f"Tool '{func_name}' not found"}
            if stream_callback:
                duration_ms = int((time.time() - start_time) * 1000)
                await stream_callback.on_tool_error(func_name, str(error_result))
            return error_result

        try:
            # 调用工具函数
            result = tool.invoke(args_dict)

            # 如果是协程，等待完成
            if asyncio.iscoroutine(result):
                result = await result

            # 转为 dict
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
            error_result = {"success": False, "error": str(e)}
            if stream_callback:
                await stream_callback.on_tool_error(func_name, str(e))
            return error_result

    def _convert_messages(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
    ) -> List[Any]:
        """将 dict 消息格式转换为 LangChain 消息格式."""
        lc_messages = []

        if system:
            lc_messages.append(SystemMessage(content=system))

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            elif role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "tool":
                lc_messages.append(
                    ToolMessage(
                        tool_call_id=msg.get("tool_call_id", ""),
                        content=content,
                    )
                )

        return lc_messages


_router: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
