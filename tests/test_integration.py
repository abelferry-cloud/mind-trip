# tests/test_integration.py
"""End-to-end integration tests for the multi-agent system.

Covers:
- Full planning flow: chat → plan retrieval
- Budget summary schema validation (reserve, category breakdowns)
- Daily routes date field validation
- Health alert generation for heart disease
- Preference update/retrieval flow
- Health endpoint with llm_primary_available
- 404 for nonexistent plan
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_full_travel_planning_flow():
    """Test complete flow: chat → get plan → verify schema compliance."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        chat_resp = await client.post("/api/chat", json={
            "user_id": "int_test_user",
            "message": "我要去杭州3天，预算5000",
            "session_id": "int_test_session"
        })
        assert chat_resp.status_code == 200
        data = chat_resp.json()
        assert "plan_id" in data
        assert "agent_trace" in data
        assert "health_alerts" in data
        plan_id = data["plan_id"]

        plan_resp = await client.get(f"/api/plan/{plan_id}")
        assert plan_resp.status_code == 200
        plan_data = plan_resp.json()
        assert plan_data["city"] == "杭州"
        assert plan_data["days"] == 3
        # Verify budget_summary schema (Design Section 5.4)
        bs = plan_data["budget_summary"]
        assert "reserve" in bs
        assert "attractions_total" in bs
        assert "food_total" in bs
        assert "hotel_total" in bs
        # Verify daily_routes date field (Design Section 5.4)
        assert "date" in plan_data["daily_routes"][0]
        # Verify health endpoint
        health_resp = await client.get("/api/health")
        assert health_resp.status_code == 200
        assert "llm_primary_available" in health_resp.json()

@pytest.mark.asyncio
async def test_preference_update_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        pref_resp = await client.put("/api/preference/int_pref_user", json={
            "key": "health", "value": ["心脏病"]
        })
        assert pref_resp.status_code == 200
        get_resp = await client.get("/api/preference/int_pref_user")
        assert get_resp.status_code == 200
        assert "health" in get_resp.json()["preferences"]

@pytest.mark.asyncio
async def test_health_alert_generated_for_heart_disease():
    """Per Health Alert Rule Table (Design Section 2.4): heart disease → rule-based alert."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/chat", json={
            "user_id": "int_hc_user",
            "message": "我要去成都2天，我有心脏病",
            "session_id": "int_hc_session"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert any("药物" in a or "剧烈" in a for a in data["health_alerts"])

@pytest.mark.asyncio
async def test_plan_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/plan/nonexistent")
        assert resp.status_code == 404
