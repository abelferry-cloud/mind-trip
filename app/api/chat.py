# app/api/chat.py
"""Chat API - main conversation endpoint."""
import asyncio
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from app.agents.supervisor import PlanningAgent
from app.config import get_settings
from app.api.plan import save_plan

router = APIRouter(prefix="/api", tags=["chat"])

class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: str

class ChatResponse(BaseModel):
    answer: str
    plan_id: str
    agent_trace: dict
    health_alerts: list
    preference_compliance: list

_agent = PlanningAgent()

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request, background_tasks: BackgroundTasks):
    """Main chat endpoint - triggers full multi-agent planning.

    Per Design Section 6.2: complete planning request has 90s timeout.
    Uses asyncio.wait_for to enforce timeout.
    """
    settings = get_settings()

    try:
        result = await asyncio.wait_for(
            _agent.plan(req.user_id, req.session_id, req.message),
            timeout=settings.request_timeout
        )
    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=200,
            content={
                "answer": "规划请求超时，请稍后重试或简化需求（如减少天数）",
                "plan_id": "",
                "agent_trace": {},
                "health_alerts": [],
                "preference_compliance": []
            }
        )

    # Save plan in background
    save_plan(result["plan_id"], result)

    return ChatResponse(
        answer=f"为您规划了{result['city']}{result['days']}天行程，祝您旅途愉快！",
        plan_id=result["plan_id"],
        agent_trace=result["agent_trace"],
        health_alerts=result.get("health_alerts", []),
        preference_compliance=result.get("preference_compliance", [])
    )
