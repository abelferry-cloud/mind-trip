"""TravelPlannerAgent - 统一的搜索规划 Agent（合并版）

替代原有的：AttractionsAgent, FoodAgent, HotelAgent, RouteAgent, SearchAgent
"""
import datetime
from typing import Any, Dict, List
from app.tools.travel_skills import (
    search_attractions,
    search_restaurants,
    search_hotels,
    plan_driving_route,
    tavily_web_search,
)


class TravelPlannerAgent:
    """整合搜索 + 规划的 Agent"""

    async def search_all(
        self, city: str, days: int, budget: float, preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """一次性搜索景点、餐厅、酒店，并根据偏好过滤"""
        attractions = search_attractions.invoke({"city": city})
        health = preferences.get("health", [])
        if any(h in health for h in ["心脏病", "高血压", "哮喘"]):
            attractions = [a for a in attractions if a.get("intensity") != "high"]

        restaurants = search_restaurants.invoke({"city": city})
        hotels = search_hotels.invoke({"city": city, "budget": budget / days})

        return {
            "attractions": attractions,
            "restaurants": restaurants,
            "hotels": hotels,
        }

    async def plan_routes(
        self, attractions: List[dict], constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """规划每日路线（使用高德地图驾车路线）"""
        days = constraints.get("days", 1)
        city = constraints.get("city", "")
        start_date = datetime.date.today() + datetime.timedelta(days=1)
        start_hour = 9

        daily_routes = []
        for i, attr in enumerate(attractions[:days]):
            try:
                route_info = plan_driving_route.invoke({
                    "origin": "酒店",
                    "destination": attr["name"],
                    "city": city,
                })
            except Exception:
                route_info = {"distance_km": 10, "duration_min": 30}

            current_date = start_date + datetime.timedelta(days=i)
            daily_routes.append({
                "day": i + 1,
                "date": current_date.isoformat(),
                "attractions": [{
                    "name": attr["name"],
                    "arrival_time": f"{start_hour:02d}:00",
                    "leave_time": f"{start_hour + 3:02d}:00",
                }],
                "transport": {
                    "from": "酒店",
                    "to": attr["name"],
                    "type": "驾车",
                    "distance_km": route_info.get("distance_km", 0),
                    "duration_minutes": route_info.get("duration_min", 0),
                },
            })
            start_hour = 14

        return {"daily_routes": daily_routes}

    async def web_search(self, query: str) -> Dict[str, Any]:
        """使用 Tavily 进行网络搜索"""
        return tavily_web_search.invoke({"query": query, "max_results": 5})
