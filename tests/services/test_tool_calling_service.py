"""tests/services/test_tool_calling_service.py - ToolCallingService 测试。"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.services.tool_calling_service import ToolCallingService
from app.services.tool_registry import register_tool


@pytest.fixture
def mock_stream_callback():
    """创建模拟的流式回调."""
    callback = MagicMock()
    callback.on_iteration = AsyncMock()
    callback.on_tool_start = AsyncMock()
    callback.on_tool_end = AsyncMock()
    callback.on_tool_error = AsyncMock()
    return callback


@pytest.fixture
def mock_tool():
    """创建一个简单的模拟工具（LangChain 风格）."""
    def simple_tool(city: str) -> dict:
        return {"city": city, "attractions": ["景点A", "景点B"]}

    # 包装成 LangChain 风格，带 invoke 方法
    class ToolWrapper:
        def __init__(self, func):
            self.func = func

        def invoke(self, args):
            return self.func(**args)

    register_tool(
        name="search_attractions",
        description="搜索景点",
        parameters={
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名称"}
            },
            "required": ["city"]
        },
        func=ToolWrapper(simple_tool),
    )
    return simple_tool


@pytest.fixture
def tool_calling_service():
    return ToolCallingService()


@pytest.mark.asyncio
async def test_call_with_tools_no_stream_callback(tool_calling_service, mock_tool):
    """验证无回调时 call_with_tools 正常工作."""
    messages = [{"role": "user", "content": "北京有什么景点？"}]
    tools = []

    with patch.object(tool_calling_service, "_call_llm") as mock_call_llm:
        # 模拟 LLM 直接返回最终回答
        mock_call_llm.return_value = {
            "role": "assistant",
            "content": "北京有很多景点，比如故宫、长城。"
        }

        result = await tool_calling_service.call_with_tools(messages, tools)

        assert result == "北京有很多景点，比如故宫、长城。"
        mock_call_llm.assert_called_once()


@pytest.mark.asyncio
async def test_streaming_callback_on_iteration(tool_calling_service, mock_tool, mock_stream_callback):
    """验证 on_iteration 在每次循环开始时被调用."""
    messages = [{"role": "user", "content": "北京有什么景点？"}]
    tools = []

    with patch.object(tool_calling_service, "_call_llm") as mock_call_llm:
        # 模拟 LLM 直接返回最终回答（1次迭代）
        mock_call_llm.return_value = {
            "role": "assistant",
            "content": "北京有很多景点。"
        }

        await tool_calling_service.call_with_tools(
            messages, tools, stream_callback=mock_stream_callback
        )

        mock_stream_callback.on_iteration.assert_called_once_with(1, tool_calling_service._max_iterations)


@pytest.mark.asyncio
async def test_streaming_callback_on_tool_calls(tool_calling_service, mock_tool, mock_stream_callback):
    """验证流式回调在工具调用时被正确触发."""
    messages = [{"role": "user", "content": "搜索北京景点"}]
    tools = [{"type": "function", "function": {"name": "search_attractions", "description": "搜索景点"}}]

    with patch.object(tool_calling_service, "_call_llm") as mock_call_llm:
        # 第一次调用返回 tool_calls，第二次返回最终回答
        mock_call_llm.side_effect = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "search_attractions",
                        "arguments": '{"city": "北京"}'
                    }
                }]
            },
            {
                "role": "assistant",
                "content": "根据搜索结果，北京有以下景点：故宫、长城。"
            }
        ]

        await tool_calling_service.call_with_tools(
            messages, tools, stream_callback=mock_stream_callback
        )

        # 验证迭代开始（每个 while 循环开始时调用）
        assert mock_stream_callback.on_iteration.call_count >= 1

        # 验证工具开始调用
        mock_stream_callback.on_tool_start.assert_called_once_with(
            "search_attractions", "call_123"
        )

        # 验证工具结束调用
        mock_stream_callback.on_tool_end.assert_called_once()
        call_args = mock_stream_callback.on_tool_end.call_args
        assert call_args[0][0] == "search_attractions"  # tool name
        assert call_args[0][1]["city"] == "北京"  # result


@pytest.mark.asyncio
async def test_streaming_callback_on_tool_error(tool_calling_service, mock_stream_callback):
    """验证工具执行失败时 on_tool_error 被调用."""
    # 注册一个会失败的工具
    def failing_tool(city: str) -> dict:
        raise Exception("工具执行失败")

    class FailingToolWrapper:
        def __init__(self, func):
            self.func = func

        def invoke(self, args):
            return self.func(**args)

    register_tool(
        name="failing_tool",
        description="一个会失败的工具",
        parameters={
            "type": "object",
            "properties": {
                "city": {"type": "string"}
            },
            "required": ["city"]
        },
        func=FailingToolWrapper(failing_tool),
    )

    messages = [{"role": "user", "content": "测试错误"}]
    tools = [{"type": "function", "function": {"name": "failing_tool", "description": "一个会失败的工具"}}]

    with patch.object(tool_calling_service, "_call_llm") as mock_call_llm:
        mock_call_llm.side_effect = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_456",
                    "type": "function",
                    "function": {
                        "name": "failing_tool",
                        "arguments": '{"city": "北京"}'
                    }
                }]
            },
            {
                "role": "assistant",
                "content": "工具执行失败了。"
            }
        ]

        await tool_calling_service.call_with_tools(
            messages, tools, stream_callback=mock_stream_callback
        )

        # 验证工具错误被通知
        mock_stream_callback.on_tool_error.assert_called_once()
        call_args = mock_stream_callback.on_tool_error.call_args
        assert call_args[0][0] == "failing_tool"  # tool name
        assert "工具执行失败" in call_args[0][1]  # error contains our message


@pytest.mark.asyncio
async def test_streaming_callback_not_required(tool_calling_service, mock_tool):
    """验证 stream_callback 为 None 时不会出错."""
    messages = [{"role": "user", "content": "测试"}]
    tools = []

    with patch.object(tool_calling_service, "_call_llm") as mock_call_llm:
        mock_call_llm.return_value = {
            "role": "assistant",
            "content": "测试完成"
        }

        # 不传 stream_callback 应该正常工作
        result = await tool_calling_service.call_with_tools(messages, tools)
        assert result == "测试完成"
