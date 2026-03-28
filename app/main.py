# app/main.py
"""FastAPI 应用入口点。"""
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.tracing import TracingMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.api import chat, plan, preference, monitor

# 配置结构化日志
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：Markdown 记忆子系统无需初始化（无状态）
    yield
    # 关闭：无状态

def create_app() -> FastAPI:
    app = FastAPI(
        title="Smart Travel Journal - Multi-Agent Trip Planner",
        description="基于 LangChain 的智能出行规划 Multi-Agent 系统",
        version="1.0.0",
        lifespan=lifespan
    )

    # 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TracingMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)

    # 路由
    app.include_router(chat.router)
    app.include_router(plan.router)
    app.include_router(preference.router)
    app.include_router(monitor.router)

    @app.get("/")
    async def root():
        return {
            "name": "Smart Travel Journal",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/api/health"
        }

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    from app.config import get_settings
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=True)