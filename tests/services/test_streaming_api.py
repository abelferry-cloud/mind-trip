"""测试流式 API 端点"""
import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


class TestStreamingAPI:
    """测试流式 API"""

    def test_chat_stream_request_model(self):
        """测试请求模型验证"""
        from app.api.chat_stream import ChatStreamRequest

        req = ChatStreamRequest(
            user_id="test_user",
            session_id="test_session",
            message="去北京3天预算5000元"
        )
        assert req.user_id == "test_user"
        assert req.session_id == "test_session"
        assert "北京" in req.message

    @pytest.mark.asyncio
    async def test_stream_manager_sse_event_format(self):
        """测试 StreamManager SSE 事件格式"""
        from app.services.streaming import StreamManager

        sm = StreamManager()
        session_id = "test-session-sse"

        # 注册 session
        queue = sm.register_session(session_id)

        # 发射一个测试事件
        await sm.emit(session_id, "test_event", {"key": "value"})

        # 获取事件
        event = await asyncio.wait_for(queue.get(), timeout=1)

        # 验证事件格式
        assert hasattr(event, 'event')
        assert hasattr(event, 'data')
        assert event.event == "test_event"
        assert event.data["key"] == "value"

        # 清理
        sm.unregister_session(session_id)

    @pytest.mark.asyncio
    async def test_stream_manager_all_event_types(self):
        """测试 StreamManager 所有事件类型"""
        from app.services.streaming import StreamManager

        sm = StreamManager()
        session_id = "test-session-all-events"

        # 注册 session
        queue = sm.register_session(session_id)

        # 测试各种事件
        events_to_test = [
            ("agent_switch", {"agent": "TestAgent"}),
            ("llm_start", {"model": "deepseek"}),
            ("llm_new_token", {"token": "hello"}),
            ("llm_end", {"total_tokens": 100}),
            ("tool_start", {"tool": "test_tool", "tool_call_id": "call_1"}),
            ("tool_end", {"tool": "test_tool", "result": "ok", "duration_ms": 50}),
            ("tool_error", {"tool": "test_tool", "error": "error"}),
            ("reasoning_start", {"description": "thinking"}),
            ("reasoning_content", {"content": "thought"}),
            ("reasoning_end", {}),
            ("iteration", {"iteration": 1, "max_iterations": 10}),
            ("error", {"error": "test error"}),
            ("final", {"answer": "final answer"}),
        ]

        for event_type, data in events_to_test:
            await sm.emit(session_id, event_type, data)

        # 验证所有事件都被正确添加
        received_events = []
        while not queue.empty():
            event = await queue.get()
            received_events.append(event)

        assert len(received_events) == len(events_to_test)

        # 验证事件类型
        received_types = [e.event for e in received_events]
        expected_types = [e[0] for e in events_to_test]
        assert received_types == expected_types

        # 清理
        sm.unregister_session(session_id)

    @pytest.mark.asyncio
    async def test_stream_callback_handler_events(self):
        """测试 StreamCallbackHandler 事件发射"""
        from app.services.streaming import StreamManager
        from app.services.streaming.stream_callback import StreamCallbackHandler

        sm = StreamManager()
        session_id = "test-session-callback"

        # 先注册 session
        sm.register_session(session_id)

        callback = StreamCallbackHandler(sm, session_id)

        # 发射各种事件
        await callback.on_llm_start("deepseek")
        await callback.on_llm_new_token("hello")
        await callback.on_llm_end(100, 50, 50)
        await callback.on_tool_start("test_tool", "call_1")
        await callback.on_tool_end("test_tool", {"result": "ok"}, 50)
        await callback.on_reasoning_step("thinking...")
        await callback.on_iteration(1, 10)
        await callback.on_agent_switch("TestAgent")
        await callback.on_final("final answer")

        # 验证事件
        queue = sm._sessions.get(session_id)
        events = []
        while not queue.empty():
            events.append(await queue.get())

        # 至少验证有事件被发射
        assert len(events) > 0

        # 清理
        sm.unregister_session(session_id)

    @pytest.mark.asyncio
    async def test_langchain_callback_handler(self):
        """测试 LangChainCallbackHandler 事件发射"""
        from app.services.streaming import StreamManager
        from app.services.streaming.stream_callback import StreamCallbackHandler
        from app.services.streaming.langchain_callback import LangChainCallbackHandler

        sm = StreamManager()
        session_id = "test-session-langchain"

        # 先注册 session
        sm.register_session(session_id)

        stream_callback = StreamCallbackHandler(sm, session_id)
        lc_callback = LangChainCallbackHandler(stream_callback, session_id)

        # 模拟 LangChain 事件
        serialized = {"id": ["deepseek"]}

        # on_chat_model_start
        await lc_callback.on_chat_model_start(serialized, [], run_id="run_1")

        # 验证 agent_switch 事件
        queue = sm._sessions.get(session_id)
        agent_switch_event = await queue.get()
        assert agent_switch_event.event == "agent_switch"

        # 清理
        sm.unregister_session(session_id)


class TestSSEEventFormat:
    """测试 SSE 事件格式"""

    def test_sse_event_data_serialization(self):
        """测试 SSE 事件数据序列化"""
        from app.services.streaming.stream_manager import SSEEvent
        import time

        event = SSEEvent(
            event="test",
            data={"key": "value", "number": 123},
            timestamp=time.time()
        )

        # 验证数据可以序列化
        data_str = json.dumps(event.data, ensure_ascii=False)
        assert "key" in data_str
        assert "value" in data_str


class TestStreamManagerSession:
    """测试 StreamManager Session 管理"""

    @pytest.mark.asyncio
    async def test_register_unregister_session(self):
        """测试 session 注册和取消注册"""
        from app.services.streaming import StreamManager

        sm = StreamManager()
        session_id = "test-session-reg"

        # 注册
        queue = sm.register_session(session_id)
        assert queue is not None

        # 再次注册同一 session 应该返回相同的队列
        queue2 = sm.register_session(session_id)
        assert queue is queue2

        # 取消注册
        sm.unregister_session(session_id)

        # 取消注册后，队列应该被删除
        assert session_id not in sm._sessions

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """测试断开连接"""
        from app.services.streaming import StreamManager

        sm = StreamManager()
        session_id = "test-session-disconnect"

        # 连接
        await sm.connect(session_id)

        # 断开
        await sm.disconnect(session_id)

        # 验证清理
        assert session_id not in sm._queues
        assert session_id not in sm._connections


class TestConfigDefaults:
    """测试配置"""

    def test_deepseek_config_exists(self):
        """测试 DeepSeek 配置存在"""
        from app.config import get_settings

        settings = get_settings()
        # 验证 DeepSeek 配置存在
        assert settings.deepseek_api_key is not None
        assert settings.deepseek_model == "deepseek-chat"
