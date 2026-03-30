# app/agents/supervisor.py
"""规划 Agent（主管）- 协调所有专家 Agent。

这是多 Agent 系统的主要入口点。
协调流程：偏好 Agent → 并行（搜索 + 预算）→ 路线 → 预算检查。
"""
import asyncio
import re
import uuid
import time
from typing import Any, Dict, List, Optional
from app.agents.preference import PreferenceAgent
from app.agents.budget import BudgetAgent
from app.agents.travel_planner import TravelPlannerAgent
from app.services.memory import get_short_term_memory
from app.services.metrics_service import get_metrics_service
from app.graph.sys_prompt_builder import get_supervisor_loader

# 健康提醒规则
_HEALTH_ALERT_RULES = {
    "心脏病": "您的行程包含较多步行，建议随身携带日常药物并避免剧烈活动",
    "糖尿病": "建议随身携带血糖仪和备用食物，注意按时用餐",
}

_HARDSHIP_ALERT_RULES = {
    "硬座": "已为您排除火车硬座选项，全程优先选择卧铺/座位",
}

def parse_travel_intent(message: str) -> Dict[str, Any]:
    """从自然语言解析用户旅行意图。

    提取：城市、天数、预算、季节。
    """
    # 提取城市（在"去"或"到"或"前往"之后）
    # 使用非贪婪 {2,5}? 匹配最少 2 个字符的城市名
    city_match = re.search(r"去([A-Za-z\u4e00-\u9fa5]{2,5}?)|到([A-Za-z\u4e00-\u9fa5]{2,5}?)|前往([A-Za-z\u4e00-\u9fa5]{2,5}?)", message)
    city = city_match.group(1) or city_match.group(2) or city_match.group(3) if city_match else ""

    # 提取天数
    days_match = re.search(r"(\d+)天", message)
    days = int(days_match.group(1)) if days_match else 2

    # 提取预算
    budget_match = re.search(r"预算(\d+)", message)
    budget = int(budget_match.group(1)) if budget_match else 3000

    # 提取季节（粗略启发式）
    season = "spring"
    if any(s in message for s in ["夏天", "夏季", "暑假", "七月", "八月"]):
        season = "summer"
    elif any(s in message for s in ["秋天", "秋季", "九月", "十月", "十一月"]):
        season = "autumn"
    elif any(s in message for s in ["冬天", "冬季", "十二月", "一月", "二月"]):
        season = "winter"

    return {"city": city, "days": days, "budget": budget, "season": season}

class PlanningAgent:
    """协调所有专家 Agent 的主管 Agent。

    协调流程：
      1. 解析意图
      2. 偏好 Agent：解析并更新偏好
      3. 并行：TravelPlanner（搜索景点/餐厅/酒店）+ 预算 Agent
      4. TravelPlanner：规划每日路线
      5. 预算 Agent：验证
      6. 如果超预算 → TravelPlanner 重新规划（最多 2 次尝试）
      7. 生成健康提醒 + 偏好合规说明
      8. 返回最终方案
    """

    def __init__(self):
        self.pref_agent = PreferenceAgent()
        self.budget_agent = BudgetAgent()
        self.travel_agent = TravelPlannerAgent()
        self.metrics = get_metrics_service()
        # Workspace 动态加载器（每次 plan() 调用时重新读取 .md 文件）
        self._prompt_loader = get_supervisor_loader(mode="main")

    async def plan(
        self,
        user_id: str,
        session_id: str,
        message: str,
        stream_callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """主要规划入口点。"""
        t0 = time.time()
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        agent_trace = {"agents": [], "invocation_order": [], "durations_ms": [], "errors": []}

        # ============================================================
        # 动态加载 System Prompt（每次请求时重新读取 workspace .md 文件）
        # ============================================================
        prompt_result = self._prompt_loader.invoke({})
        system_prompt = prompt_result["system_prompt"]

        async def trace(agent_name: str, coro, stream_callback=None):
            """包装器用于计时 Agent 调用，并可选地发射 agent_switch 事件。"""
            agent_trace["agents"].append(agent_name)
            agent_trace["invocation_order"].append(len(agent_trace["agents"]))
            t = time.time()

            # 发射 agent_switch 事件
            if stream_callback:
                await stream_callback.on_agent_switch(agent_name)

            try:
                result = await coro
                agent_trace["durations_ms"].append(int((time.time() - t) * 1000))
                return result
            except Exception as e:
                agent_trace["durations_ms"].append(int((time.time() - t) * 1000))
                agent_trace["errors"].append({"agent": agent_name, "error": str(e)})
                raise

        # 步骤 1：解析意图
        intent = parse_travel_intent(message)
        city, days, budget, season = intent["city"], intent["days"], intent["budget"], intent["season"]

        # 步骤 2：解析并更新偏好
        pref_result = await trace("Preference Agent",
            self.pref_agent.parse_and_update(user_id, message), stream_callback)
        preferences = await self.pref_agent.get_preference(user_id)

        # 步骤 3：并行 - 搜索（景点/餐厅/酒店）+ 预算计算
        search_result, budget_result = await asyncio.gather(
            trace("TravelPlanner Agent (search)", self.travel_agent.search_all(city, days, budget, preferences), stream_callback),
            trace("Budget Agent", self.budget_agent.calculate(days, preferences.get("spending_style", "适中")), stream_callback)
        )
        attractions = search_result.get("attractions", [])
        restaurants = search_result.get("restaurants", [])
        hotels = search_result.get("hotels", [])

        # 步骤 4：路线规划
        route_result = await trace("TravelPlanner Agent (route)",
            self.travel_agent.plan_routes(attractions, {
                "days": days,
                "city": city,
                "preferred_start_time": "09:00",
            }), stream_callback)

        # 步骤 5：餐厅/酒店已包含在 search_result 中，无需单独获取

        # 步骤 6：预算验证
        hotel_info = hotels[0] if hotels else {}
        hotel_cost = 0  # Amap POI doesn't return prices directly
        plan_summary = {
            "daily_routes": route_result.get("daily_routes", []),
            "hotel": {"name": hotel_info.get("name", ""), "total_cost": hotel_cost},
            "transport_to_city": {"type": "高铁", "cost": 220},  # 模拟：进城交通
            "attractions_total": sum(a.get("ticket_price", 0) for a in attractions),
            "food_total": len(restaurants) * (budget // days // 3),
            "transport_within_city": days * 30,  # 估算市内交通
        }

        budget_check = await trace("Budget Agent (validation)",
            self.budget_agent.check_plan(budget, plan_summary), stream_callback)

        # 步骤 7：预算 → 路线调整循环（最多 2 次尝试）
        if not budget_check["within_budget"] and budget_check["alerts"]:
            for attempt in [1, 2]:
                route_result = await trace("TravelPlanner Agent (replan)",
                    self.travel_agent.plan_routes(attractions, {
                        "days": days,
                        "city": city,
                        "preferred_start_time": "09:00",
                        "replan_context": {"mode": "replan", "reason": "over_budget", "attempt": attempt}
                    }), stream_callback)
                plan_summary["daily_routes"] = route_result.get("daily_routes", [])
                budget_check = await trace("Budget Agent (revalidation)",
                    self.budget_agent.check_plan(budget, plan_summary), stream_callback)
                if budget_check["within_budget"]:
                    break

        # 步骤 8：生成健康提醒和偏好合规
        health_alerts = self._generate_health_alerts(preferences)
        preference_compliance = self._generate_compliance(preferences)

        # 保存到短期记忆
        short_mem = get_short_term_memory(session_id)
        short_mem.save_context(
            {"input": message},
            {"output": f"已为您规划{city}{days}天行程，预算{budget}元"}
        )

        total_ms = int((time.time() - t0) * 1000)
        self.metrics.increment("chat_requests_total")
        self.metrics.record_latency("chat", total_ms)

        # 计算备用金 = 总预算 - sum(类别花费)
        total_cost = (
            plan_summary["attractions_total"]
            + plan_summary["food_total"]
            + hotel_cost
            + plan_summary["transport_to_city"]["cost"]
            + plan_summary["transport_within_city"]
        )
        reserve = budget - total_cost

        # 从 calculate_budget 调用获取类别细分
        cat_breakdown = budget_result  # 来自 calculate_budget 调用

        # 构造自然语言回答
        answer = f"已为您规划 {city} {days} 天行程，预算 {budget} 元。\n\n"

        if route_result.get("daily_routes"):
            answer += "每日行程：\n"
            for i, route in enumerate(route_result["daily_routes"][:3], 1):  # 最多显示3天
                answer += f"第{i}天：{route.get('title', '自由活动')}\n"

        budget_summary = {
            "total_budget": budget,
            "attractions_total": plan_summary["attractions_total"],
            "food_total": plan_summary["food_total"],
            "hotel_total": hotel_cost,
            "transport_total": plan_summary["transport_to_city"]["cost"] + plan_summary["transport_within_city"],
            "reserve": max(0, reserve),
            "within_budget": budget_check["within_budget"],
            "remaining": budget_check.get("remaining", 0),
            "alerts": budget_check.get("alerts", [])
        }

        if budget_summary.get("within_budget") is False:
            answer += f"\n预算提醒：您的预算可能不足，剩余 {budget_summary.get('remaining', 0)} 元"

        if health_alerts:
            answer += "\n\n健康提醒：" + "；".join(health_alerts[:2])  # 最多2条

        total_cost = budget_summary.get('attractions_total', 0) + budget_summary.get('food_total', 0) + budget_summary.get('hotel_total', 0) + budget_summary.get('transport_total', 0)
        answer += f"\n\n预算总计：{total_cost} 元"

        # ========== 流式生成最终答案 ==========
        if stream_callback:
            # 构建总结 prompt
            summary_prompt = self._build_summary_prompt(
                city=city,
                days=days,
                budget=budget,
                daily_routes=route_result.get("daily_routes", []),
                attractions=attractions,
                restaurants=restaurants,
                budget_summary=budget_summary,
                health_alerts=health_alerts,
                preference_compliance=preference_compliance,
            )

            # 调用 LLM 流式生成最终答案
            answer = await self.stream_generate(summary_prompt, stream_callback)
        # ====================================

        return {
            "plan_id": plan_id,
            "city": city,
            "days": days,
            "budget": budget,
            "answer": answer,
            "system_prompt": system_prompt,  # 动态加载的系统提示词
            "daily_routes": route_result.get("daily_routes", []),
            "attractions": attractions,
            "food": restaurants,
            "hotels": hotels,
            "budget_summary": budget_summary,
            "health_alerts": health_alerts,
            "preference_compliance": preference_compliance,
            "agent_trace": agent_trace,
        }

    def _generate_health_alerts(self, preferences: Dict[str, Any]) -> List[str]:
        alerts = []
        for condition, alert_text in _HEALTH_ALERT_RULES.items():
            if condition in preferences.get("health", []):
                alerts.append(alert_text)
        # 未列出的健康状况的备用提醒
        for h in preferences.get("health", []):
            if h not in _HEALTH_ALERT_RULES:
                alerts.append(f"请注意：{h}")
        return alerts

    def _generate_compliance(self, preferences: Dict[str, Any]) -> List[str]:
        notes = []
        for hardship, note in _HARDSHIP_ALERT_RULES.items():
            if hardship in preferences.get("hardships", []):
                notes.append(note)
        return notes

    async def stream_generate(self, prompt: str, stream_callback) -> str:
        """流式生成最终答案（通过 ModelRouter）。"""
        from app.services.model import get_model_router
        router = get_model_router()

        # 发射 agent_switch
        await stream_callback.on_agent_switch("Final Answer Generator")

        # 构建消息
        messages = [{"role": "user", "content": prompt}]

        # 调用 ModelRouter（不带工具）
        result = await router.call_with_tools(
            messages=messages,
            system="你是一个旅行规划助手，用简洁的语言生成最终行程方案。",
            stream_callback=stream_callback,
        )
        return result

    def _build_summary_prompt(
        self,
        city: str,
        days: int,
        budget: int,
        daily_routes: List,
        attractions: List,
        restaurants: List,
        budget_summary: Dict,
        health_alerts: List,
        preference_compliance: List,
    ) -> str:
        """构建总结 prompt，用于生成最终答案。"""
        prompt = f"""请用自然语言生成一段简洁的旅行规划回复，包含以下信息：

目的地：{city}
天数：{days}天
预算：{budget}元

行程安排：
"""
        for i, route in enumerate(daily_routes[:3], 1):
            prompt += f"第{i}天：{route.get('title', '自由活动')}\n"

        prompt += f"""
预算安排：
- 景点门票：{budget_summary.get('attractions_total', 0)}元
- 餐饮：{budget_summary.get('food_total', 0)}元
- 交通：{budget_summary.get('transport_total', 0)}元
"""
        if health_alerts:
            prompt += f"\n健康提醒：{'；'.join(health_alerts)}\n"
        if preference_compliance:
            prompt += f"偏好合规：{'；'.join(preference_compliance)}\n"

        prompt += "\n请用简洁友好的语言生成回复。"
        return prompt