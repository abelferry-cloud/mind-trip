# app/agents/hotel.py
"""Hotel Agent - search hotels."""
from typing import Dict, Any, List
from app.tools import hotel_tools as ht

class HotelAgent:
    """Specialist agent for hotel search."""

    async def search(self, city: str, budget: float = 500.0, location: str = "") -> Dict[str, Any]:
        hotels = await ht.search_hotels(city, budget, location)
        return {"hotels": hotels}
