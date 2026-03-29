"""酒店工具 - 委托给 travel_skills"""
from typing import List, Dict, Any
from app.tools.travel_skills import search_hotels

async def search_hotels(city: str, budget: float = 500.0, location_preference: str = "") -> List[Dict[str, Any]]:
    """搜索酒店（委托给 travel_skills）"""
    result = search_hotels.invoke({"city": city, "budget": budget, "location": location_preference})
    return [
        {
            "name": r.get("name", ""),
            "location": r.get("address", ""),
            "price_per_night": budget,
            "rating": 4.5,
        }
        for r in result
    ]
