# app/agents/route.py
"""Route Agent - plan daily routes."""
from typing import Dict, Any, List
from app.tools import route_tools as rt

class RouteAgent:
    """Specialist agent for route planning."""

    async def plan(self, attractions: List[dict], constraints: Dict[str, Any]) -> Dict[str, Any]:
        """Plan daily routes given attractions and constraints."""
        daily_routes = await rt.plan_daily_route(attractions, constraints)
        return {"daily_routes": daily_routes}

    async def estimate_travel(self, from_location: str, to_location: str, transport: str) -> Dict[str, Any]:
        return await rt.estimate_travel_time(from_location, to_location, transport)
