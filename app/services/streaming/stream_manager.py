"""app/services/streaming/stream_manager.py - SSE 事件发射器单例。

维护每个 session_id -> asyncio.Queue 的映射，供各服务发射 SSE 事件。
"""
import asyncio
import json
from typing import Any, Dict, Optional


class StreamManager:
    """SSE 事件发射器。

    单例模式。每个 session_id 对应一个 asyncio.Queue。
    发射事件时，将格式化后的 SSE 数据放入对应队列。
    SSE 端点从队列中读取并推送给客户端。
    """

    def __init__(self):
        self._sessions: Dict[str, asyncio.Queue] = {}
        self._lock = asyncio.Lock()

    def register_session(self, session_id: str) -> asyncio.Queue:
        """注册一个会话，返回其事件队列。"""
        return self._sessions.setdefault(session_id, asyncio.Queue())

    def unregister_session(self, session_id: str) -> None:
        """注销一个会话，清理其队列。"""
        self._sessions.pop(session_id, None)

    async def emit(
        self,
        session_id: str,
        event_name: str,
        data: Any,
    ) -> None:
        """发射 SSE 事件到指定会话的队列。

        Args:
            session_id: 会话 ID
            event_name: 事件名（如 'tool_start'）
            data: 事件数据（会被 JSON 序列化）
        """
        queue = self._sessions.get(session_id)
        if queue is None:
            # 调试：session 未注册时记录但不抛出异常
            import logging
            logging.warning(f"Session {session_id} not found for event {event_name}")
            return

        event_line = f"event: {event_name}\n"
        data_line = f"data: {json.dumps(data)}\n\n"
        await queue.put(event_line + data_line)

    async def emit_comment(self, session_id: str, comment: str) -> None:
        """发射 SSE comment（用于心跳等）。"""
        queue = self._sessions.get(session_id)
        if queue is None:
            return
        await queue.put(f": {comment}\n\n")

    async def get_event(self, session_id: str) -> Optional[str]:
        """从队列获取事件（阻塞等待）。超时返回 None。"""
        queue = self._sessions.get(session_id)
        if queue is None:
            return None
        try:
            return await asyncio.wait_for(queue.get(), timeout=60.0)
        except asyncio.TimeoutError:
            return None

    # ---- 便捷方法 ----

    async def agent_switch(self, session_id: str, agent: str, description: str = "") -> None:
        await self.emit(session_id, "agent_switch", {"agent": agent, "description": description})

    async def model_switch(
        self, session_id: str, model: str, reason: str
    ) -> None:
        await self.emit(session_id, "model_switch", {"model": model, "reason": reason})

    async def iteration(
        self, session_id: str, iteration: int, max_iterations: int
    ) -> None:
        await self.emit(
            session_id, "iteration",
            {"iteration": iteration, "max_iterations": max_iterations}
        )

    async def tool_start(
        self, session_id: str, tool: str, tool_call_id: str
    ) -> None:
        await self.emit(
            session_id, "tool_start",
            {"tool": tool, "tool_call_id": tool_call_id}
        )

    async def tool_end(
        self, session_id: str, tool: str, summary: Any, duration_ms: int
    ) -> None:
        await self.emit(
            session_id, "tool_end",
            {"tool": tool, "summary": summary, "duration_ms": duration_ms}
        )

    async def tool_error(self, session_id: str, tool: str, error: str) -> None:
        await self.emit(
            session_id, "tool_error",
            {"tool": tool, "error": error}
        )

    async def skill_start(
        self, session_id: str, skill: str, tool_call_id: str
    ) -> None:
        await self.emit(
            session_id, "skill_start",
            {"skill": skill, "tool_call_id": tool_call_id}
        )

    async def skill_end(
        self, session_id: str, skill: str, summary: Any, duration_ms: int
    ) -> None:
        await self.emit(
            session_id, "skill_end",
            {"skill": skill, "summary": summary, "duration_ms": duration_ms}
        )

    async def llm_start(self, session_id: str, model: str) -> None:
        await self.emit(session_id, "llm_start", {"model": model})

    async def llm_end(
        self,
        session_id: str,
        total_tokens: int,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        await self.emit(
            session_id,
            "llm_end",
            {
                "total_tokens": total_tokens,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            }
        )

    async def token_usage(
        self, session_id: str,
        prompt_tokens: int, completion_tokens: int, total_tokens: int
    ) -> None:
        await self.emit(
            session_id, "token_usage",
            {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            }
        )

    async def reasoning_step(self, session_id: str, step: str) -> None:
        await self.emit(session_id, "reasoning_step", {"step": step})

    async def content_chunk(self, session_id: str, content: str) -> None:
        await self.emit(session_id, "content_chunk", {"content": content})

    async def final(self, session_id: str, answer: str) -> None:
        await self.emit(session_id, "final", {"answer": answer})

    async def error(self, session_id: str, error: str) -> None:
        await self.emit(session_id, "error", {"error": error})

    async def ping(self, session_id: str) -> None:
        await self.emit_comment(session_id, "ping")


# 单例
_stream_manager: Optional[StreamManager] = None
_stream_manager_lock = asyncio.Lock()


async def get_stream_manager() -> StreamManager:
    global _stream_manager
    if _stream_manager is None:
        async with _stream_manager_lock:
            # Double-check after acquiring lock
            if _stream_manager is None:
                _stream_manager = StreamManager()
    return _stream_manager
