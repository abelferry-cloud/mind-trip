# tests/api/test_chat.py
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from app.api.chat import router as chat_router
from fastapi import FastAPI

# Create a test app using the chat router directly
app = FastAPI()
app.include_router(chat_router)

@pytest.mark.asyncio
async def test_chat_returns_plan_id():
    mock_result = {
        "plan_id": "test_plan_123",
        "city": "杭州",
        "days": 3,
        "agent_trace": {"agents": [], "invocation_order": [], "durations_ms": [], "errors": []},
        "health_alerts": [],
        "preference_compliance": []
    }
    with patch("app.api.chat._agent") as mock_agent:
        mock_agent.plan = AsyncMock(return_value=mock_result)
        with patch("app.api.chat.save_plan"):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/chat", json={
                    "user_id": "test_user",
                    "message": "我要去杭州3天，预算5000",
                    "session_id": "test_session"
                })
                assert resp.status_code == 200
                data = resp.json()
                assert "plan_id" in data
                assert data["plan_id"] == "test_plan_123"
                assert "answer" in data

@pytest.mark.asyncio
async def test_chat_timeout_returns_fallback():
    with patch("app.api.chat._agent") as mock_agent:
        mock_agent.plan = AsyncMock(side_effect=TimeoutError())
        with patch("app.api.chat.asyncio.wait_for", side_effect=TimeoutError()):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/chat", json={
                    "user_id": "test_user",
                    "message": "我要去杭州3天，预算5000",
                    "session_id": "test_session"
                })
                assert resp.status_code == 200
                data = resp.json()
                assert data["plan_id"] == ""
                assert "超时" in data["answer"]
