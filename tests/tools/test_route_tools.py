# tests/tools/test_route_tools.py
import pytest
from app.tools.route_tools import plan_daily_route, estimate_travel_time

@pytest.mark.asyncio
async def test_plan_daily_route():
    attractions = [
        {"id": "attr_hz_001", "name": "西湖", "intensity": "low"},
        {"id": "attr_hz_002", "name": "灵隐寺", "intensity": "medium"},
    ]
    constraints = {
        "days": 2,
        "budget_limit": 1000.0,
        "mobility_limitations": [],
        "preferred_start_time": "09:00",
        "transport_preferences": ["地铁", "公交", "出租车"],
        "replan_context": None
    }
    route = await plan_daily_route(attractions, constraints)
    assert len(route) == 2
    assert route[0]["day"] == 1
    assert len(route[0]["attractions"]) == 1

@pytest.mark.asyncio
async def test_estimate_travel_time():
    result = await estimate_travel_time("酒店", "西湖", "地铁")
    assert "duration_minutes" in result
    assert "distance_km" in result
    assert result["duration_minutes"] > 0