"""Search Agent - 统一封装 Tavily + 高德地图搜索"""
from typing import Any, Dict, List
from app.tools import search_tools as st


class SearchAgent:
    """统一搜索 Agent，整合 Tavily 和高德地图。

    对外暴露单一接口，内部路由到合适的搜索工具。
    """

    async def search_attractions(
        self, city: str, days: int, season: str, preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """搜索景点并根据用户偏好过滤。"""
        attractions = await st.amap_attractions(city, page_size=20)

        # 健康偏好过滤（心脏病/高血压/哮喘患者不适合高强度）
        health_prefs = preferences.get("health", [])
        if any(h in health_prefs for h in ["心脏病", "高血压", "哮喘"]):
            attractions = [a for a in attractions if a.get("intensity") != "high"]

        return {"attractions": attractions, "city": city, "days": days}

    async def search_restaurants(
        self, city: str, style: str = "", budget_per_meal: float = 100.0
    ) -> Dict[str, Any]:
        """推荐餐厅。"""
        restaurants = await st.amap_restaurants(city, page_size=20)
        if style:
            restaurants = [r for r in restaurants if style in r.get("cuisine", "")]
        # 按预算过滤
        restaurants = [r for r in restaurants if r.get("avg_budget", 9999) <= budget_per_meal * 1.5]
        return {"restaurants": restaurants}

    async def search_hotels(
        self, city: str, budget: float = 500.0, location: str = ""
    ) -> Dict[str, Any]:
        """搜索酒店。"""
        hotels = await st.amap_hotels(city, budget=budget, page_size=20)
        if location:
            hotels = [h for h in hotels if location in h.get("location", "")]
        return {"hotels": hotels}

    async def plan_route(
        self, attractions: List[dict], constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """规划每日路线，使用高德地图路线规划。"""
        import datetime

        days = constraints.get("days", 1)
        replan = constraints.get("replan_context")

        # 过滤高强度景点（重试模式下进一步精简）
        filtered = attractions
        mobility = constraints.get("mobility_limitations", [])
        if mobility:
            filtered = [a for a in filtered if a.get("intensity") != "high"]
            if not filtered:
                filtered = attractions

        if replan and replan.get("attempt") == 2:
            filtered = filtered[:days]

        city = constraints.get("city", "")
        start_date = datetime.date.today() + datetime.timedelta(days=1)
        daily_routes = []
        start_hour = int(constraints.get("preferred_start_time", "09:00").split(":")[0])

        for day_num in range(1, days + 1):
            if day_num - 1 >= len(filtered):
                break
            attr = filtered[day_num - 1]
            attr_name = attr.get("name", "")

            # 调用高德地图估算从酒店到景点的路线
            try:
                route_info = await st.amap_route("酒店", attr_name, city, "driving")
            except Exception:
                route_info = {"distance_km": 10, "duration_min": 30}

            current_date = start_date + datetime.timedelta(days=day_num - 1)
            daily_routes.append({
                "day": day_num,
                "date": current_date.isoformat(),
                "attractions": [{
                    "id": attr.get("id", ""),
                    "name": attr_name,
                    "arrival_time": f"{start_hour:02d}:00",
                    "leave_time": f"{start_hour + 3:02d}:00",
                }],
                "transport": {
                    "from": "酒店",
                    "to": attr_name,
                    "type": "驾车",
                    "distance_km": route_info.get("distance_km", 0),
                    "duration_minutes": route_info.get("duration_min", 0),
                },
                "meals": [{"type": "午餐", "restaurant": "待推荐", "budget": 100}],
            })
            start_hour = 14

        return {"daily_routes": daily_routes}
