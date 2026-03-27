# app/tools/route_tools.py
"""路线工具 - 规划每日路线和估算旅行时间。
带有确定性输出的模拟实现用于演示。
"""
from typing import List, Dict, Any, Optional
import datetime

# 模拟旅行时间估算（from_location, to_location, transport）→ (duration_min, distance_km)
_MOCK_TRAVEL = {
    ("酒店", "西湖", "地铁"): (25, 8),
    ("酒店", "灵隐寺", "地铁"): (35, 12),
    ("西湖", "灵隐寺", "地铁"): (20, 7),
    ("西湖", "灵隐寺", "出租车"): (15, 6),
    ("灵隐寺", "酒店", "地铁"): (35, 12),
    ("西湖", "酒店", "地铁"): (20, 6),
}

def _get_travel_time(from_loc: str, to_loc: str, transport: str) -> tuple:
    for (f, t, tr), (dur, dist) in _MOCK_TRAVEL.items():
        if from_loc in f and to_loc in t:
            return dur, dist
    # Default estimate
    return (30, 10) if "地铁" in transport else (20, 8)

async def plan_daily_route(
    attractions: List[dict],
    constraints: dict
) -> List[Dict[str, Any]]:
    """根据景点和约束条件规划每日路线。

    Args:
        attractions: 来自 search_attractions 的景点列表
        constraints: {
            "days": int,
            "budget_limit": float,
            "mobility_limitations": List[str],
            "preferred_start_time": str,
            "transport_preferences": List[str],
            "replan_context": dict | None
        }

    Returns:
        每日计划列表，包含天数、日期、景点、交通、餐食
        根据设计文档第 5.4 节：每个 daily_route 包含 date 字段
    """
    days = constraints["days"]
    replan = constraints.get("replan_context")

    # 如果存在行动限制，过滤掉高强度景点
    filtered = attractions
    if constraints.get("mobility_limitations"):
        filtered = [a for a in attractions if a.get("intensity", "medium") != "high"]
        if len(filtered) == 0:
            filtered = attractions  # 如果全部被过滤则回退

    # 根据重新规划尝试次数调整策略
    if replan:
        attempt = replan.get("attempt", 1)
        if attempt == 1:
            pass  # 保留最多景点，仅预算削减
        elif attempt == 2:
            filtered = filtered[:days] if len(filtered) >= days else filtered

    # 分配开始日期（今天 +1 作为模拟出发日期）
    start_date = datetime.date.today() + datetime.timedelta(days=1)

    daily_plans = []
    start_hour = int(constraints.get("preferred_start_time", "09:00").split(":")[0])
    transport_pref = constraints.get("transport_preferences", ["地铁"])[0]

    idx = 0
    for day_num in range(1, days + 1):
        if idx >= len(filtered):
            break
        attr = filtered[idx]
        travel_from_hotel = _get_travel_time("酒店", attr["name"], transport_pref)
        current_date = start_date + datetime.timedelta(days=day_num - 1)
        daily_plans.append({
            "day": day_num,
            "date": current_date.isoformat(),  # e.g., "2026-04-01"
            "attractions": [{
                "id": attr["id"],
                "name": attr["name"],
                "arrival_time": f"{start_hour:02d}:00",
                "leave_time": f"{start_hour + 3:02d}:00"
            }],
            "transport": {
                "from": "酒店",
                "to": attr["name"],
                "type": transport_pref,
                "duration_minutes": travel_from_hotel[0]
            },
            "meals": [
                {"type": "午餐", "restaurant": "外婆家（景区店）", "budget": 80}
            ]
        })
        start_hour = 14
        idx += 1

    return daily_plans

async def estimate_travel_time(from_location: str, to_location: str, transport: str) -> Dict[str, Any]:
    """估算两个地点之间的旅行时间。"""
    dur, dist = _get_travel_time(from_location, to_location, transport)
    return {"duration_minutes": dur, "distance_km": dist}