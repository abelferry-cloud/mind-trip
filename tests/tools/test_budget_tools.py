# tests/tools/test_budget_tools.py
import pytest
from app.tools.budget_tools import calculate_budget, check_budget_vs_plan

@pytest.mark.asyncio
async def test_calculate_budget():
    result = await calculate_budget(3, "节省")
    assert "total_budget" in result
    assert "attractions_budget" in result
    assert "food_budget" in result
    assert "hotel_budget" in result

@pytest.mark.asyncio
async def test_check_budget_within():
    plan = {
        "daily_routes": [{"attractions": [{"ticket_price": 0}], "transport": {"estimated_cost": 20}, "meals": [{"estimated_cost": 80}]}],
        "hotel": {"total_cost": 450},
        "transport_to_city": {"cost": 220},
        "attractions_total": 0,
        "food_total": 240,
        "transport_within_city": 60
    }
    result = await check_budget_vs_plan(5000.0, plan)
    assert result["within_budget"] is True

@pytest.mark.asyncio
async def test_check_budget_over():
    plan = {
        "daily_routes": [],
        "hotel": {"total_cost": 10000},
        "transport_to_city": {"cost": 0},
        "attractions_total": 0,
        "food_total": 0,
        "transport_within_city": 0
    }
    result = await check_budget_vs_plan(5000.0, plan)
    assert result["within_budget"] is False
    assert result["remaining"] < 0