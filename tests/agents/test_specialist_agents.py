# tests/agents/test_specialist_agents.py
import pytest
from app.agents.attractions import AttractionsAgent
from app.agents.route import RouteAgent
from app.agents.budget import BudgetAgent
from app.agents.food import FoodAgent
from app.agents.hotel import HotelAgent

@pytest.mark.asyncio
async def test_attractions_agent():
    agent = AttractionsAgent()
    prefs = {"health": ["心脏病"], "hardships": ["硬座"]}
    result = await agent.search("杭州", 3, "spring", prefs)
    assert "attractions" in result
    assert all(a.get("intensity") != "high" for a in result["attractions"])

@pytest.mark.asyncio
async def test_route_agent():
    agent = RouteAgent()
    attractions = [{"id": "attr_hz_001", "name": "西湖", "intensity": "low", "ticket_price": 0}]
    constraints = {"days": 1, "budget_limit": 1000, "mobility_limitations": [],
                   "preferred_start_time": "09:00", "transport_preferences": ["地铁"], "replan_context": None}
    result = await agent.plan(attractions, constraints)
    assert "daily_routes" in result

@pytest.mark.asyncio
async def test_budget_agent():
    agent = BudgetAgent()
    result = await agent.calculate(3, "适中")
    assert result["total_budget"] > 0

@pytest.mark.asyncio
async def test_food_agent():
    agent = FoodAgent()
    result = await agent.recommend("杭州", "浙菜", 100.0)
    assert len(result) > 0

@pytest.mark.asyncio
async def test_hotel_agent():
    agent = HotelAgent()
    result = await agent.search("杭州", 300.0, "西湖区")
    assert len(result) > 0
