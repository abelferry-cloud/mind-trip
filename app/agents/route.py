# app/agents/route.py
"""路线 Agent - 规划每日路线。"""
from typing import Dict, Any, List
from app.tools import route_tools as rt

class RouteAgent:
    """路线规划专家 Agent。"""

    async def plan(self, attractions: List[dict], constraints: Dict[str, Any]) -> Dict[str, Any]:
        """根据景点和约束条件规划每日路线。"""
        daily_routes = await rt.plan_daily_route(attractions, constraints)
        return {"daily_routes": daily_routes}

    async def estimate_travel(self, from_location: str, to_location: str, transport: str) -> Dict[str, Any]:
        return await rt.estimate_travel_time(from_location, to_location, transport)
