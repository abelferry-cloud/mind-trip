"""app/api/chat_stream.py - SSE 流式输出端点。

POST /api/chat/stream
- 请求体同 /api/chat
- 响应: text/event-stream
- 通过 StreamManager 获取 session 对应的事件队列
- 心跳 ping (15s interval)
"""
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import asyncio
import json

from app.services.stream_manager import get_stream_manager
from app.services.chat_service import get_chat_service
from app.config import get_settings

router = APIRouter(prefix="/api", tags=["chat"])


class ChatStreamRequest(BaseModel):
    user_id: str
    message: str
    session_id: str


@router.post("/chat/stream")
async def chat_stream(
    req: ChatStreamRequest,
    background_tasks: BackgroundTasks,
):
    """SSE 流式对话端点。

    流程:
    1. 注册 session 到 StreamManager
    2. 启动后台任务处理 chat
    3. 返回 SSE 事件流
    """
    stream_manager = await get_stream_manager()
    settings = get_settings()

    # 注册 session
    queue = stream_manager.register_session(req.session_id)

    # 启动后台任务处理 chat
    # 注意: BackgroundTasks 必须作为路径操作函数参数传入才会执行
    chat_service = get_chat_service()
    background_tasks.add_task(
        chat_service.chat_stream,
        req.user_id,
        req.session_id,
        req.message,
    )

    # SSE 事件流生成器
    async def event_generator():
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
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
