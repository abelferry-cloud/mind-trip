"""美食工具 - 委托给 travel_skills"""
from typing import List, Dict, Any
from app.tools.travel_skills import search_restaurants

async def recommend_restaurants(city: str, style: str = "", budget_per_meal: float = 100.0) -> List[Dict[str, Any]]:
    """推荐餐厅（委托给 travel_skills）"""
    result = search_restaurants.invoke({"city": city, "cuisine": style})
    return [
        {
            "name": r.get("name", ""),
            "cuisine": r.get("type", ""),
            "price_level": "¥",
            "location": r.get("address", ""),
            "avg_budget": budget_per_meal,
        }
        for r in result
    ]
