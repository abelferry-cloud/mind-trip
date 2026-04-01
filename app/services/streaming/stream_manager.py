"""StreamManager - SSE 事件发射器.

管理 SSE 连接池，向上层模块提供事件发射接口.
"""
import asyncio
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()


@dataclass
class SSEEvent:
    """SSE 事件数据结构."""
    event: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


class StreamManager:
    """SSE 流管理器.

    负责：
    - 管理 session -> SSE queue 的映射
    - 接收事件并通过 SSE 发射
    - 连接生命周期管理
    """

    def __init__(self):
        # session_id -> asyncio.Queue
        self._queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        # session_id -> set of active connections
        self._connections: Dict[str, set] = defaultdict(set)
        # session_id -> metadata
        self._metadata: Dict[str, Dict[str, Any]] = {}
        # session_id -> SSEvent (兼容旧代码)
        self._sessions: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)

    async def connect(self, session_id: str) -> asyncio.Queue:
        """建立 SSE 连接，返回事件队列.

        Args:
            session_id: 会话 ID

        Returns:
            asyncio.Queue，调用者从队列中获取事件
        """
        queue = self._queues[session_id]
        logger.info("stream_connected", session_id=session_id)
        return queue

    def register_session(self, session_id: str) -> asyncio.Queue:
        """注册 session，返回队列（兼容旧代码）."""
        return self._sessions[session_id]

    def unregister_session(self, session_id: str) -> None:
        """取消注册 session（兼容旧代码）."""
        if session_id in self._sessions:
            del self._sessions[session_id]

    async def get_event(self, session_id: str) -> Optional[str]:
        """获取事件（兼容旧代码）."""
        import json
        if session_id not in self._sessions:
            return None
        try:
            event = await asyncio.wait_for(self._sessions[session_id].get(), timeout=1)
            if hasattr(event, 'event') and hasattr(event, 'data'):
                data_str = json.dumps(event.data, ensure_ascii=False)
                return f"event: {event.event}\ndata: {data_str}"
            return str(event)
        except asyncio.TimeoutError:
            return None

    async def disconnect(self, session_id: str) -> None:
        """断开 SSE 连接.

        Args:
            session_id: 会话 ID
        """
        if session_id in self._queues:
            del self._queues[session_id]
        if session_id in self._connections:
            del self._connections[session_id]
        if session_id in self._metadata:
            del self._metadata[session_id]
        if session_id in self._sessions:
            del self._sessions[session_id]
        logger.info("stream_disconnected", session_id=session_id)

    async def emit(
        self,
        session_id: str,
        event_type: str,
        data: Dict[str, Any],
    ) -> None:
        """发射通用事件.

        Args:
            session_id: 会话 ID
            event_type: 事件类型
            data: 事件数据
        """
        # 检查 _queues 或 _sessions
        if session_id not in self._queues and session_id not in self._sessions:
            logger.warning("stream_not_found", session_id=session_id)
            return

        event = SSEEvent(event=event_type, data=data)
        try:
            # 优先使用 _queues，然后使用 _sessions
            if session_id in self._queues:
                self._queues[session_id].put_nowait(event)
            else:
                self._sessions[session_id].put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("stream_queue_full", session_id=session_id)

    # ================================================================
    # 事件发射方法
    # ================================================================

    async def agent_switch(
        self,
        session_id: str,
        agent: str,
        description: str = "",
    ) -> None:
        """发射 agent_switch 事件（Agent 切换）."""
        await self.emit(session_id, "agent_switch", {
            "agent": agent,
            "description": description,
            "timestamp": time.time(),
        })

    async def llm_start(self, session_id: str, model: str) -> None:
        """发射 llm_start 事件（LLM 开始推理）."""
        await self.emit(session_id, "llm_start", {
            "model": model,
            "timestamp": time.time(),
        })

    async def llm_new_token(self, session_id: str, token: str) -> None:
        """发射 llm_new_token 事件（新 token，用于打字机效果）."""
        await self.emit(session_id, "llm_new_token", {
            "token": token,
            "timestamp": time.time(),
        })

    async def llm_end(
        self,
        session_id: str,
        total_tokens: int,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
    ) -> None:
        """发射 llm_end 事件（LLM 生成完成 + token 统计）."""
        await self.emit(session_id, "llm_end", {
            "total_tokens": total_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": cost_usd,
            "timestamp": time.time(),
        })

    async def tool_start(
        self,
        session_id: str,
        tool: str,
        tool_call_id: str,
    ) -> None:
        """发射 tool_start 事件（工具开始调用）."""
        await self.emit(session_id, "tool_start", {
            "tool": tool,
            "tool_call_id": tool_call_id,
            "timestamp": time.time(),
        })

    async def tool_call(
        self,
        session_id: str,
        tool: str,
        arguments: Dict[str, Any],
        tool_call_id: str,
    ) -> None:
        """发射 tool_call 事件（工具调用请求，包含参数）."""
        await self.emit(session_id, "tool_call", {
            "tool": tool,
            "arguments": arguments,
            "tool_call_id": tool_call_id,
            "timestamp": time.time(),
        })

    async def tool_end(
        self,
        session_id: str,
        tool: str,
        result: Any,
        duration_ms: int,
    ) -> None:
        """发射 tool_end 事件（工具执行完成）."""
        await self.emit(session_id, "tool_end", {
            "tool": tool,
            "result": result,
            "duration_ms": duration_ms,
            "timestamp": time.time(),
        })

    async def tool_error(
        self,
        session_id: str,
        tool: str,
        error: str,
    ) -> None:
        """发射 tool_error 事件（工具执行失败）."""
        await self.emit(session_id, "tool_error", {
            "tool": tool,
            "error": error,
            "timestamp": time.time(),
        })

    async def reasoning_start(self, session_id: str, description: str = "") -> None:
        """发射 reasoning_start 事件（推理阶段开始）."""
        await self.emit(session_id, "reasoning_start", {
            "description": description,
            "timestamp": time.time(),
        })

    async def reasoning_content(self, session_id: str, content: str) -> None:
        """发射 reasoning_content 事件（推理内容片段）."""
        await self.emit(session_id, "reasoning_content", {
            "content": content,
            "timestamp": time.time(),
        })

    async def reasoning_step(self, session_id: str, content: str) -> None:
        """发射 reasoning_step 事件（推理步骤，reasoning_content 的别名）."""
        await self.emit(session_id, "reasoning_content", {
            "content": content,
            "timestamp": time.time(),
        })

    async def reasoning_end(self, session_id: str) -> None:
        """发射 reasoning_end 事件（推理阶段结束）."""
        await self.emit(session_id, "reasoning_end", {
            "timestamp": time.time(),
        })

    async def iteration(
        self,
        session_id: str,
        iteration: int,
        max_iterations: int,
    ) -> None:
        """发射 iteration 事件（工具调用循环次数）."""
        await self.emit(session_id, "iteration", {
            "iteration": iteration,
            "max_iterations": max_iterations,
            "timestamp": time.time(),
        })

    async def model_switch(
        self,
        session_id: str,
        model: str,
        reason: str,
    ) -> None:
        """发射 model_switch 事件（模型切换）."""
        await self.emit(session_id, "model_switch", {
            "model": model,
            "reason": reason,
            "timestamp": time.time(),
        })

    async def error(
        self,
        session_id: str,
        error: str,
        recoverable: bool = True,
    ) -> None:
        """发射 error 事件（错误）."""
        await self.emit(session_id, "error", {
            "error": error,
            "recoverable": recoverable,
            "timestamp": time.time(),
        })

    async def final(self, session_id: str, answer: str) -> None:
        """发射 final 事件（最终回复）."""
        await self.emit(session_id, "final", {
            "answer": answer,
            "timestamp": time.time(),
        })

    async def phase_start(
        self,
        session_id: str,
        phase: str,
        description: str = "",
    ) -> None:
        """发射 phase_start 事件（阶段开始）."""
        await self.emit(session_id, "phase_start", {
            "phase": phase,
            "description": description,
            "timestamp": time.time(),
        })

    async def skill_start(
        self,
        session_id: str,
        skill: str,
        tool_call_id: str,
    ) -> None:
        """发射 skill_start 事件（Skill/Tool 开始调用）."""
        await self.emit(session_id, "skill_start", {
            "skill": skill,
            "tool_call_id": tool_call_id,
            "timestamp": time.time(),
        })

    async def skill_end(
        self,
        session_id: str,
        skill: str,
        summary: Any,
        duration_ms: int,
    ) -> None:
        """发射 skill_end 事件（Skill/Tool 结束）."""
        await self.emit(session_id, "skill_end", {
            "skill": skill,
            "summary": summary,
            "duration_ms": duration_ms,
            "timestamp": time.time(),
        })

    async def plan_start(
        self,
        session_id: str,
        city: str,
        days: int,
        budget: float,
    ) -> None:
        """发射 plan_start 事件（规划开始）."""
        await self.emit(session_id, "plan_start", {
            "city": city,
            "days": days,
            "budget": budget,
            "timestamp": time.time(),
        })

    async def plan_end(
        self,
        session_id: str,
        plan_id: str,
    ) -> None:
        """发射 plan_end 事件（规划完成）."""
        await self.emit(session_id, "plan_end", {
            "plan_id": plan_id,
            "timestamp": time.time(),
        })

    async def metadata_update(
        self,
        session_id: str,
        key: str,
        value: Any,
    ) -> None:
        """发射 metadata_update 事件（元数据更新）."""
        await self.emit(session_id, "metadata_update", {
            "key": key,
            "value": value,
            "timestamp": time.time(),
        })


# 全局单例
_stream_manager: Optional[StreamManager] = None


async def get_stream_manager() -> StreamManager:
    """获取 StreamManager 单例."""
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = StreamManager()
    return _stream_manager


def get_stream_manager_sync() -> StreamManager:
    """同步获取 StreamManager 单例."""
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = StreamManager()
    return _stream_manager
