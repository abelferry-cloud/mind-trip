# app/middleware/error_handler.py
"""错误处理中间件 - 优雅降级并提供结构化错误响应。"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import get_settings
import structlog

logger = structlog.get_logger()

class AgentError(Exception):
    def __init__(self, agent_name: str, message: str, recoverable: bool = False):
        self.agent_name = agent_name
        self.message = message
        self.recoverable = recoverable

class AllAgentsFailedError(Exception):
    pass

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except AgentError as e:
            logger.error("agent_error", agent=e.agent_name, message=e.message, recoverable=e.recoverable)
            return JSONResponse(
                status_code=200 if e.recoverable else 500,
                content={
                    "error": e.message,
                    "agent": e.agent_name,
                    "recoverable": e.recoverable,
                    "fallback": "请告诉我更具体的偏好，或稍后重试"
                }
            )
        except AllAgentsFailedError:
            logger.error("all_agents_failed")
            return JSONResponse(
                status_code=200,
                content={
                    "answer": "抱歉，所有推荐服务暂时不可用。请稍后重试，或告诉我更具体的需求。",
                    "fallback": "您可以尝试说 '我要去杭州' 这样的简单需求"
                }
            )
        except Exception as e:
            logger.exception("unhandled_error")
            return JSONResponse(
                status_code=500,
                content={"error": "服务内部错误，请稍后重试"}
            )