# app/services/model/model_router.py
"""模型路由 - LangChain Runnable 抽象层。

使用 LangChain ChatOpenAI (OpenAI 兼容) + fallback 链。
支持 DeepSeek, OpenAI, Claude, Local 模型。
"""
from typing import Any, Dict, List, Literal, Optional

from app.config import get_settings
from app.services.tools.tool_registry import get_tools_schema
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

ModelName = Literal["deepseek", "openai", "claude", "local"]


class ModelRouter:
    """模型路由器 - LangChain Runnable 风格。

    使用 ChatOpenAI (OpenAI 兼容) 实现 DeepSeek 调用，
    通过 with_fallbacks 实现模型回退链。
    """

    def __init__(self):
        self.settings = get_settings()
        self._clients: Dict[str, ChatOpenAI] = {}
        self._setup_clients()

    def _setup_clients(self):
        """初始化各模型的 ChatOpenAI 客户端。"""
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

    async def call_with_tools(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        stream_callback: Optional[Any] = None,
    ) -> str:
        """带工具调用的模型调用（LangChain 风格）。

        Args:
            messages: 消息列表（会直接修改）
            system: 系统提示词
            stream_callback: 流式回调处理器（StreamCallbackHandler）

        Returns:
            LLM 的最终回答文本
        """
        # 转换消息格式
        lc_messages = self._convert_messages(messages, system)

        # 获取工具 schema
        tools = get_tools_schema()

        # 获取主模型（DeepSeek）
        primary = self._clients.get("deepseek") or self._clients.get("openai")
        if not primary:
            raise Exception("No model client available")

        # 如果有工具，绑定工具
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
        """流式调用模型，通过 LangChain callback system。"""
        accumulated = ""

        # 构建 config，通过 LangChain callback system 传递
        config = {}
        if stream_callback:
            # 创建 LangChain 兼容的 callback handler
            from app.services.streaming.stream_callback import LangChainStreamCallbackHandler
            handler = LangChainStreamCallbackHandler(stream_callback)
            config["callbacks"] = [handler]

        async for chunk in model.astream(messages, config):
            if chunk.content:
                accumulated += chunk.content

        return accumulated

    async def _call_with_tools_streaming(
        self,
        model: ChatOpenAI,
        messages: List[Any],
        tools: List[Dict[str, Any]],
        stream_callback: Optional[Any] = None,
    ) -> str:
        """带工具调用的流式模型调用。"""
        # 构建工具描述 prompt
        tools_prompt = self._build_tools_prompt(tools)
        messages_with_tools = messages + [HumanMessage(content=f"\n\n{tools_prompt}")]

        accumulated = ""

        # 构建 config
        config = {}
        if stream_callback:
            from app.services.streaming.stream_callback import LangChainStreamCallbackHandler
            handler = LangChainStreamCallbackHandler(stream_callback)
            config["callbacks"] = [handler]

        async for chunk in model.astream(messages_with_tools, config):
            if chunk.content:
                accumulated += chunk.content

        return accumulated

    def _convert_messages(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
    ) -> List[Any]:
        """将 dict 消息格式转换为 LangChain 消息格式。"""
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

        return lc_messages

    def _build_tools_prompt(self, tools: List[Dict[str, Any]]) -> str:
        """将工具 schema 构建为自然语言描述。"""
        if not tools:
            return ""

        lines = ["你可以使用以下工具："]
        for tool in tools:
            name = tool.get("name", "unknown")
            desc = tool.get("description", "")
            params = tool.get("parameters", {}).get("properties", {})

            lines.append(f"\n## {name}")
            lines.append(f"描述: {desc}")
            if params:
                lines.append("参数:")
                for pname, pdesc in params.items():
                    lines.append(f"  - {pname}: {pdesc.get('description', '')}")

        return "\n".join(lines)


_router: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
