# app/agents/attractions.py
"""Attractions Agent - search and filter attractions based on user preferences."""
from typing import Dict, Any, List
from app.tools import attractions_tools as at

class AttractionsAgent:
    """Specialist agent for attractions search and filtering.

    Reads preferences from Preference Agent to filter out inappropriate attractions
    (e.g., high-intensity for heart disease patients).
    """

    async def search(self, city: str, days: int, season: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Search attractions and filter based on user preferences."""
        attractions = await at.search_attractions(city, days, season)

        # Filter based on health preferences
        health_prefs = preferences.get("health", [])
        mobility_limitations = []
        if any(h in health_prefs for h in ["心脏病", "高血压", "哮喘"]):
            mobility_limitations.append("high_intensity")

        filtered = attractions
        if mobility_limitations:
            filtered = [a for a in attractions if a.get("intensity") != "high"]

        return {"attractions": filtered, "city": city, "days": days}

    async def get_detail(self, attraction_id: str) -> Dict[str, Any]:
        return await at.get_attraction_detail(attraction_id)

    async def check_availability(self, attraction_id: str, date: str) -> Dict[str, Any]:
        return await at.check_availability(attraction_id, date)
