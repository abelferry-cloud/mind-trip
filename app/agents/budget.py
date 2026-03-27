# app/agents/budget.py
"""预算 Agent - 计算和验证预算。"""
from typing import Dict, Any
from app.tools import budget_tools as bt

class BudgetAgent:
    """预算计算和验证专家 Agent。"""

    async def calculate(self, duration: int, style: str) -> Dict[str, Any]:
        return await bt.calculate_budget(duration, style)

    async def check_plan(self, budget: float, plan: dict) -> Dict[str, Any]:
        return await bt.check_budget_vs_plan(budget, plan)
