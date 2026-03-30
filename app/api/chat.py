# app/api/chat.py
"""聊天 API - 基于动态 System Prompt 的对话端点。

核心流程：
1. 每次请求时，WorkspacePromptLoader 动态加载 workspace/*.md 为 System Prompt
2. 将 System Prompt + User Message 发送给模型
3. 返回模型的思考结果

暂不包含：工具调用、记忆存储、多 Agent 规划流程
"""
import asyncio
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from app.services.chat import get_chat_service
from app.config import get_settings

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: str


class ChatResponse(BaseModel):
    answer: str
    metadata: dict
    reasoning: Optional[dict] = None


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request, background_tasks: BackgroundTasks):
    """对话端点 - 基于动态 System Prompt 的智能问答。

    每次请求时：
    1. 从 workspace/*.md 动态加载 System Prompt
    2. 将 System Prompt + User Message 发送给模型
    3. 返回模型回复
    """
    settings = get_settings()
    chat_service = get_chat_service()

    try:
        result = await asyncio.wait_for(
            chat_service.chat(req.user_id, req.session_id, req.message),
            timeout=settings.request_timeout,
        )
    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=200,
            content={
                "answer": "请求超时，请稍后重试",
                "metadata": {"model": "", "timestamp": ""},
                "reasoning": None,
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={
                "answer": f"出错了：{str(e)}",
                "metadata": {"model": "", "timestamp": ""},
                "reasoning": None,
            }
        )

    return ChatResponse(
        answer=result["answer"],
        metadata=result.get("metadata", {}),
        reasoning=result.get("reasoning"),
    )
