# app/tools/budget_tools.py
"""预算工具 - 计算预算分配并与方案对比验证。
"""
from typing import Dict, Any

# 预算风格乘数（相对于基准中档）
_BUDGET_STYLES = {
    "节省": {"multiplier": 0.6, "attractions_pct": 0.10, "food_pct": 0.25, "hotel_pct": 0.35, "transport_pct": 0.15, "reserve_pct": 0.15},
    "适中": {"multiplier": 1.0, "attractions_pct": 0.15, "food_pct": 0.25, "hotel_pct": 0.30, "transport_pct": 0.10, "reserve_pct": 0.20},
    "奢侈": {"multiplier": 2.0, "attractions_pct": 0.20, "food_pct": 0.25, "hotel_pct": 0.30, "transport_pct": 0.10, "reserve_pct": 0.15},
}

async def calculate_budget(duration: int, style: str = "适中") -> Dict[str, Any]:
    """计算旅行预算细分。

    Args:
        duration: 天数
        style: "节省" | "适中" | "奢侈"

    Returns:
        {"total_budget": float, "attractions_budget": float, "food_budget": float,
         "hotel_budget": float, "transport_budget": float, "reserve_budget": float}
    """
    base = 1500 * duration  # 基准中档：每天 1500 CNY
    style_cfg = _BUDGET_STYLES.get(style, _BUDGET_STYLES["适中"])
    total = int(base * style_cfg["multiplier"])

    return {
        "total_budget": total,
        "attractions_budget": int(total * style_cfg["attractions_pct"]),
        "food_budget": int(total * style_cfg["food_pct"]),
        "hotel_budget": int(total * style_cfg["hotel_pct"]),
        "transport_budget": int(total * style_cfg["transport_pct"]),
        "reserve_budget": int(total * style_cfg["reserve_pct"]),
    }

async def check_budget_vs_plan(budget: float, plan: dict) -> Dict[str, Any]:
    """检查方案是否超出预算。

    plan: 见设计文档第 4.3 节
    Returns: {"within_budget": bool, "remaining": float, "alerts": List[str]}
    """
    # 累加方案中的实际花费
    daily_costs = 0
    for route in plan.get("daily_routes", []):
        for attr in route.get("attractions", []):
            daily_costs += attr.get("ticket_price", 0)
        for meal in route.get("meals", []):
            daily_costs += meal.get("estimated_cost", 0)
        daily_costs += route.get("transport", {}).get("estimated_cost", 0)

    hotel_cost = plan.get("hotel", {}).get("total_cost", 0)
    transport_to = plan.get("transport_to_city", {}).get("cost", 0)
    attractions_total = plan.get("attractions_total", 0)
    food_total = plan.get("food_total", 0)
    transport_within = plan.get("transport_within_city", 0)

    total_cost = daily_costs + hotel_cost + transport_to + attractions_total + food_total + transport_within
    remaining = budget - total_cost

    alerts = []
    if remaining < 0:
        alerts.append(f"当前方案超出预算 {-remaining:.0f} 元")
    if remaining < budget * 0.1:
        alerts.append("预算余量不足10%，建议增加预算或精简行程")

    return {
        "within_budget": remaining >= 0,
        "remaining": round(remaining, 2),
        "alerts": alerts
    }