# app/tools/route_tools.py
"""Route Tools - plan daily routes and estimate travel time.
Mock implementation with deterministic output for demonstration.
"""
from typing import List, Dict, Any, Optional
import datetime

# Mock travel time estimates (from_location, to_location, transport) → (duration_min, distance_km)
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
    """Plan daily route given attractions and constraints.

    Args:
        attractions: List of attraction dicts from search_attractions
        constraints: {
            "days": int,
            "budget_limit": float,
            "mobility_limitations": List[str],
            "preferred_start_time": str,
            "transport_preferences": List[str],
            "replan_context": dict | None
        }

    Returns:
        List of daily plans with day number, date, attractions, transport, meals
        Per Design Section 5.4: each daily_route includes date field
    """
    days = constraints["days"]
    replan = constraints.get("replan_context")

    # Filter out high-intensity attractions if mobility_limitations present
    filtered = attractions
    if constraints.get("mobility_limitations"):
        filtered = [a for a in attractions if a.get("intensity", "medium") != "high"]
        if len(filtered) == 0:
            filtered = attractions  # fallback if all are filtered out

    # Adjust strategy based on replan attempt
    if replan:
        attempt = replan.get("attempt", 1)
        if attempt == 1:
            pass  # keep most attractions, just budget-trim
        elif attempt == 2:
            filtered = filtered[:days] if len(filtered) >= days else filtered

    # Assign start date (today + 1 as mock departure date)
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
    """Estimate travel time between two locations."""
    dur, dist = _get_travel_time(from_location, to_location, transport)
    return {"duration_minutes": dur, "distance_km": dist}