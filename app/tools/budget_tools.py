# app/tools/budget_tools.py
"""预算工具 - 计算预算分配并与方案对比验证。

改造为标准 LangChain Tool 格式，使用 Pydantic Schema 和 ToolResult 返回格式。
"""
from typing import Annotated, Dict, Any

from pydantic import BaseModel, Field
from langchain_core.tools import tool

from app.tools.base import ToolResult, ToolException, ToolErrorCategory

# 预算风格乘数（相对于基准中档）
_BUDGET_STYLES = {
    "节省": {"multiplier": 0.6, "attractions_pct": 0.10, "food_pct": 0.25, "hotel_pct": 0.35, "transport_pct": 0.15, "reserve_pct": 0.15},
    "适中": {"multiplier": 1.0, "attractions_pct": 0.15, "food_pct": 0.25, "hotel_pct": 0.30, "transport_pct": 0.10, "reserve_pct": 0.20},
    "奢侈": {"multiplier": 2.0, "attractions_pct": 0.20, "food_pct": 0.25, "hotel_pct": 0.30, "transport_pct": 0.10, "reserve_pct": 0.15},
}


class BudgetCalculateInput(BaseModel):
    """预算计算输入模型

    用于 calculate_budget 工具的参数校验
    """
    duration: Annotated[int, Field(ge=1, le=30, description="旅行天数（1-30天）")]
    style: Annotated[str, Field(description='预算风格: "节省" | "适中" | "奢侈"')] = "适中"


class BudgetCheckInput(BaseModel):
    """预算验证输入模型

    用于 check_budget_vs_plan 工具的参数校验
    """
    budget: Annotated[float, Field(ge=0, description="总预算金额")]
    plan: Annotated[dict, Field(description="旅行方案完整数据")]


@tool(args_schema=BudgetCalculateInput)
async def calculate_budget(
    duration: Annotated[int, "旅行天数（1-30天）"],
    style: Annotated[str, '预算风格: "节省" | "适中" | "奢侈"'] = "适中"
) -> ToolResult:
    """计算旅行预算细分。

    根据旅行天数和预算风格，计算各项预算分配：
    景点、餐饮、住宿、交通、预备金。

    Args:
        duration: 旅行天数
        style: 预算风格

    Returns:
        ToolResult: 包含预算分配详情的标准工具结果
    """
    try:
        base = 1500 * duration  # 基准中档：每天 1500 CNY
        style_cfg = _BUDGET_STYLES.get(style, _BUDGET_STYLES["适中"])
        total = int(base * style_cfg["multiplier"])

        data = {
            "total_budget": total,
            "attractions_budget": int(total * style_cfg["attractions_pct"]),
            "food_budget": int(total * style_cfg["food_pct"]),
            "hotel_budget": int(total * style_cfg["hotel_pct"]),
            "transport_budget": int(total * style_cfg["transport_pct"]),
            "reserve_budget": int(total * style_cfg["reserve_pct"]),
        }

        return ToolResult(success=True, data=data, metadata={"tool_name": "calculate_budget"})

    except Exception as e:
        return ToolResult(
            success=False,
            error=ToolException(
                category=ToolErrorCategory.UNKNOWN_ERROR,
                message=f"预算计算失败: {str(e)}",
                details={"duration": duration, "style": style}
            ),
            metadata={"tool_name": "calculate_budget"}
        )


@tool(args_schema=BudgetCheckInput)
async def check_budget_vs_plan(
    budget: Annotated[float, "总预算金额"],
    plan: Annotated[dict, "旅行方案完整数据"]
) -> ToolResult:
    """检查旅行方案是否超出预算。

    遍历方案中的各项花费，计算总费用并与预算对比，
    生成超支警告和预算余量提示。

    Args:
        budget: 总预算
        plan: 旅行方案（包含 hotel, transport_to_city, attractions_total, food_total 等）

    Returns:
        ToolResult: 包含是否超预算、剩余金额、警告信息的标准工具结果
    """
    try:
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

        data = {
            "within_budget": remaining >= 0,
            "remaining": round(remaining, 2),
            "alerts": alerts
        }

        return ToolResult(success=True, data=data, metadata={"tool_name": "check_budget_vs_plan"})

    except Exception as e:
        return ToolResult(
            success=False,
            error=ToolException(
                category=ToolErrorCategory.UNKNOWN_ERROR,
                message=f"预算校验失败: {str(e)}",
                details={"budget": budget}
            ),
            metadata={"tool_name": "check_budget_vs_plan"}
        )