# tests/agents/test_supervisor_agent.py
import pytest
from unittest.mock import AsyncMock, patch
from app.agents.supervisor import PlanningAgent, parse_travel_intent

def test_parse_travel_intent_full():
    # "杭州" is 2 characters - regex matches {2,5} chars after "去"
    result = parse_travel_intent("我要去杭州玩3天，预算5000")
    assert result["city"] == "杭州"
    assert result["days"] == 3
    assert result["budget"] == 5000

def test_parse_travel_intent_partial():
    result = parse_travel_intent("我想去成都")
    assert result["city"] == "成都"
    assert result["days"] == 2  # default
    assert result["budget"] == 3000  # default

def test_parse_travel_intent_season():
    result = parse_travel_intent("夏天去杭州玩2天")
    assert result["city"] == "杭州"
    assert result["season"] == "summer"

@pytest.mark.asyncio
async def test_full_planning_flow():
    agent = PlanningAgent()
    # Mock individual agent methods since implementation calls them directly
    with patch.object(agent.pref_agent, "parse_and_update", new_callable=AsyncMock) as mock_parse, \
         patch.object(agent.pref_agent, "get_preference", new_callable=AsyncMock) as mock_get_pref, \
         patch.object(agent.attr_agent, "search", new_callable=AsyncMock) as mock_attr, \
         patch.object(agent.budget_agent, "calculate", new_callable=AsyncMock) as mock_calc, \
         patch.object(agent.route_agent, "plan", new_callable=AsyncMock) as mock_route, \
         patch.object(agent.food_agent, "recommend", new_callable=AsyncMock) as mock_food, \
         patch.object(agent.hotel_agent, "search", new_callable=AsyncMock) as mock_hotel, \
         patch.object(agent.budget_agent, "check_plan", new_callable=AsyncMock) as mock_check:

        mock_parse.return_value = {"updated": []}
        mock_get_pref.return_value = {"hardships": [], "health": [], "spending_style": "适中"}
        mock_attr.return_value = {"attractions": [{"id": "attr_hz_001", "name": "西湖", "intensity": "low", "ticket_price": 0}]}
        mock_calc.return_value = {"total_budget": 5000}
        mock_route.return_value = {"daily_routes": []}
        mock_food.return_value = {"restaurants": []}
        mock_hotel.return_value = {"hotels": []}
        mock_check.return_value = {"within_budget": True, "remaining": 1000, "alerts": []}

        result = await agent.plan("u1", "sess_1", "我要去杭州3天，预算5000")
        assert "plan_id" in result
        assert result["city"] == "杭州"
        assert result["days"] == 3
        assert result["budget"] == 5000