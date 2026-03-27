# app/agents/food.py
"""Food Agent - recommend restaurants."""
from typing import Dict, Any, List
from app.tools import food_tools as ft

class FoodAgent:
    """Specialist agent for food recommendations."""

    async def recommend(self, city: str, style: str = "", budget_per_meal: float = 100.0) -> Dict[str, Any]:
        restaurants = await ft.recommend_restaurants(city, style, budget_per_meal)
        return {"restaurants": restaurants}
