# app/agents/budget.py
"""Budget Agent - calculate and validate budgets."""
from typing import Dict, Any
from app.tools import budget_tools as bt

class BudgetAgent:
    """Specialist agent for budget calculation and validation."""

    async def calculate(self, duration: int, style: str) -> Dict[str, Any]:
        return await bt.calculate_budget(duration, style)

    async def check_plan(self, budget: float, plan: dict) -> Dict[str, Any]:
        return await bt.check_budget_vs_plan(budget, plan)
