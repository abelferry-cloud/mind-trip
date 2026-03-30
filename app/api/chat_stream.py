"""app/api/chat_stream.py - SSE 流式输出端点。

POST /api/chat/stream - 发送消息并返回 SSE 流
GET /api/chat/stream - EventSource 连接（用于前端接收事件）

两种方式共享同一个 session 队列：
1. POST 时注册 session，启动后台任务处理 chat
2. GET 用于 EventSource 连接，前端通过此接收事件流
"""
from fastapi import APIRouter, BackgroundTasks, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import asyncio

from app.services.streaming import get_stream_manager
from app.services.chat import get_chat_service
from app.config import get_settings

router = APIRouter(prefix="/api", tags=["chat"])


class ChatStreamRequest(BaseModel):
    user_id: str
    message: str
    session_id: str


async def _create_sse_generator(session_id: str, queue: asyncio.Queue):
    """创建 SSE 事件流生成器（供 POST 和 GET 共同使用）。"""
    stream_manager = await get_stream_manager()
    try:
        # 发送初始连接事件
        yield f"event: connected\ndata: {{}}\n\n"

        # 心跳间隔 (15s)
        ping_interval = 15

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=ping_interval)
                yield event
            except asyncio.TimeoutError:
                # 发送心跳
                yield f": ping\n\n"
    except GeneratorExit:
        pass
    finally:
        # Clean up session on exit
        stream_manager.unregister_session(session_id)


@router.post("/chat/stream")
async def chat_stream_post(
    req: ChatStreamRequest,
    background_tasks: BackgroundTasks,
):
    """POST 端点：触发消息处理（不返回 stream）。

    前端应使用 EventSource GET 端点来接收 SSE 事件。
    流程:
    1. 注册 session 到 StreamManager
    2. 启动后台任务处理 chat
    3. 立即返回（后台任务通过 StreamManager 发射事件）
    """
    stream_manager = await get_stream_manager()

    # 注册 session
    queue = stream_manager.register_session(req.session_id)

    # 启动后台任务处理 chat
    chat_service = get_chat_service()
    background_tasks.add_task(
        chat_service.chat_stream,
        req.user_id,
        req.session_id,
        req.message,
    )

    # 返回确认而非 SSE stream（前端通过 EventSource GET 接收事件）
    return {"status": "processing", "session_id": req.session_id}


@router.get("/chat/stream")
async def chat_stream_get(
    session_id: str = Query(..., description="会话 ID"),
):
    """GET 端点：EventSource 连接，用于接收事件流。

    前端使用 EventSource 连接此端点来接收 SSE 事件。
    注意：需要先通过 POST 端点触发后台任务并注册 session。
    """
    stream_manager = await get_stream_manager()

    # 获取已注册的 session 队列
    queue = stream_manager._sessions.get(session_id)
    if queue is None:
        # Session 未注册，返回错误
        return JSONResponse(
            status_code=404,
            content={"error": f"Session {session_id} not found. Please POST first."}
        )

    return StreamingResponse(
        _create_sse_generator(session_id, queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
