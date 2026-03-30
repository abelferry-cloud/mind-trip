import pytest
from app.tools.budget_tools import (
    calculate_budget,
    check_budget_vs_plan,
    BudgetCalculateInput,
    BudgetCheckInput,
)


class TestBudgetCalculateInput:
    def test_valid_input(self):
        data = BudgetCalculateInput(duration=5, style="适中")
        assert data.duration == 5
        assert data.style == "适中"

    def test_duration_bounds(self):
        # 天数太小
        with pytest.raises(Exception):
            BudgetCalculateInput(duration=0, style="适中")

        # 天数太大
        with pytest.raises(Exception):
            BudgetCalculateInput(duration=31, style="适中")

    def test_default_style(self):
        data = BudgetCalculateInput(duration=3)
        assert data.style == "适中"


class TestCalculateBudget:
    @pytest.mark.asyncio
    async def test_calculate_budget_economy(self):
        result = await calculate_budget.ainvoke({"duration": 3, "style": "节省"})
        assert result.success is True
        assert "total_budget" in result.data
        assert result.data["total_budget"] > 0

    @pytest.mark.asyncio
    async def test_calculate_budget_moderate(self):
        result = await calculate_budget.ainvoke({"duration": 3, "style": "适中"})
        assert result.success is True
        assert result.data["total_budget"] > 0
        assert "attractions_budget" in result.data
        assert "food_budget" in result.data
        assert "hotel_budget" in result.data

    @pytest.mark.asyncio
    async def test_calculate_budget_luxury(self):
        result = await calculate_budget.ainvoke({"duration": 3, "style": "奢侈"})
        assert result.success is True
        assert result.data["total_budget"] > 0


class TestCheckBudgetEdgeCases:
    @pytest.mark.asyncio
    async def test_check_budget_zero(self):
        """测试预算为0的情况"""
        result = await check_budget_vs_plan.ainvoke({"budget": 0, "plan": {}})
        assert result.success is True
        assert result.data["within_budget"] is True
        assert result.data["remaining"] >= 0

    @pytest.mark.asyncio
    async def test_check_budget_empty_plan(self):
        """测试空方案的情况"""
        result = await check_budget_vs_plan.ainvoke({"budget": 1000, "plan": {}})
        assert result.success is True
        assert result.data["within_budget"] is True


class TestCheckBudgetVsPlan:
    @pytest.mark.asyncio
    async def test_within_budget(self):
        budget = 5000
        plan = {
            "daily_routes": [],
            "hotel": {"total_cost": 1000},
            "transport_to_city": {"cost": 500},
            "attractions_total": 500,
            "food_total": 1000,
            "transport_within_city": 500,
        }
        result = await check_budget_vs_plan.ainvoke({"budget": budget, "plan": plan})
        assert result.success is True
        assert result.data["within_budget"] is True
        assert result.data["remaining"] >= 0

    @pytest.mark.asyncio
    async def test_over_budget(self):
        budget = 1000
        plan = {
            "daily_routes": [],
            "hotel": {"total_cost": 5000},
            "transport_to_city": {"cost": 500},
            "attractions_total": 500,
            "food_total": 1000,
            "transport_within_city": 500,
        }
        result = await check_budget_vs_plan.ainvoke({"budget": budget, "plan": plan})
        assert result.success is True
        assert result.data["within_budget"] is False
        assert result.data["remaining"] < 0
        assert len(result.data["alerts"]) > 0
