# app/agents/hotel.py
"""酒店 Agent - 搜索酒店。"""
from typing import Dict, Any, List
from app.tools import hotel_tools as ht

class HotelAgent:
    """酒店搜索专家 Agent。"""

    async def search(self, city: str, budget: float = 500.0, location: str = "") -> Dict[str, Any]:
        hotels = await ht.search_hotels(city, budget, location)
        return {"hotels": hotels}
