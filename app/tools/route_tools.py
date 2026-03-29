"""路线工具 - 委托给 travel_skills"""
from typing import List, Dict, Any
import datetime
from app.tools.travel_skills import plan_driving_route

async def plan_daily_route(attractions: List[dict], constraints: dict) -> List[Dict[str, Any]]:
    """规划每日路线（委托给 travel_skills）"""
    days = constraints.get("days", 1)
    city = constraints.get("city", "")
    start_date = datetime.date.today() + datetime.timedelta(days=1)
    start_hour = 9

    filtered = attractions
    if constraints.get("mobility_limitations"):
        filtered = [a for a in attractions if a.get("intensity", "medium") != "high"]
        if not filtered:
            filtered = attractions

    replan = constraints.get("replan_context")
    if replan and replan.get("attempt") == 2:
        filtered = filtered[:days]

    daily_plans = []
    for i, attr in enumerate(filtered[:days]):
        try:
            route_info = plan_driving_route.invoke({
                "origin": "酒店",
                "destination": attr.get("name", ""),
                "city": city,
            })
        except Exception:
            route_info = {"distance_km": 10, "duration_min": 30}

        current_date = start_date + datetime.timedelta(days=i)
        daily_plans.append({
            "day": i + 1,
            "date": current_date.isoformat(),
            "attractions": [{
                "id": attr.get("id", ""),
                "name": attr.get("name", ""),
                "arrival_time": f"{start_hour:02d}:00",
                "leave_time": f"{start_hour + 3:02d}:00"
            }],
            "transport": {
                "from": "酒店",
                "to": attr.get("name", ""),
                "type": "驾车",
                "duration_minutes": route_info.get("duration_min", 30)
            },
            "meals": [{"type": "午餐", "restaurant": "待推荐", "budget": 100}]
        })
        start_hour = 14

    return daily_plans

async def estimate_travel_time(from_location: str, to_location: str, transport: str) -> Dict[str, Any]:
    """估算旅行时间（暂不支持）"""
    return {"duration_minutes": 30, "distance_km": 10}
