# app/agents/supervisor.py
"""Planning Agent (Supervisor) - coordinates all specialist agents.

This is the main entry point for the Multi-Agent system.
Orchestrates: Preference Agent → parallel (Attractions + Budget) → Route → parallel (Food + Hotel) → Budget check.
"""
import re
import uuid
import time
from typing import Any, Dict, List, Optional
from app.agents.preference import PreferenceAgent
from app.agents.attractions import AttractionsAgent
from app.agents.route import RouteAgent
from app.agents.budget import BudgetAgent
from app.agents.food import FoodAgent
from app.agents.hotel import HotelAgent
from app.memory.short_term import get_short_term_memory
from app.services.metrics_service import get_metrics_service

# Health alert rules
_HEALTH_ALERT_RULES = {
    "心脏病": "您的行程包含较多步行，建议随身携带日常药物并避免剧烈活动",
    "糖尿病": "建议随身携带血糖仪和备用食物，注意按时用餐",
}

_HARDSHIP_ALERT_RULES = {
    "硬座": "已为您排除火车硬座选项，全程优先选择卧铺/座位",
}

def parse_travel_intent(message: str) -> Dict[str, Any]:
    """Parse user travel intent from natural language.

    Extracts: city, days, budget, season from user message.
    """
    # Extract city (after "去" or "到" or "前往")
    # Use non-greedy {2,5}? to match minimum 2 chars for city names
    city_match = re.search(r"去([A-Za-z\u4e00-\u9fa5]{2,5}?)|到([A-Za-z\u4e00-\u9fa5]{2,5}?)|前往([A-Za-z\u4e00-\u9fa5]{2,5}?)", message)
    city = city_match.group(1) or city_match.group(2) or city_match.group(3) if city_match else ""

    # Extract days
    days_match = re.search(r"(\d+)天", message)
    days = int(days_match.group(1)) if days_match else 2

    # Extract budget
    budget_match = re.search(r"预算(\d+)", message)
    budget = int(budget_match.group(1)) if budget_match else 3000

    # Extract season (rough heuristic)
    season = "spring"
    if any(s in message for s in ["夏天", "夏季", "暑假", "七月", "八月"]):
        season = "summer"
    elif any(s in message for s in ["秋天", "秋季", "九月", "十月", "十一月"]):
        season = "autumn"
    elif any(s in message for s in ["冬天", "冬季", "十二月", "一月", "二月"]):
        season = "winter"

    return {"city": city, "days": days, "budget": budget, "season": season}

class PlanningAgent:
    """Supervisor agent that coordinates all specialist agents.

    Orchestration flow (see Design Doc Section 2.3):
      1. Parse intent
      2. Preference Agent: parse and update preferences
      3. Parallel: Attractions Agent + Budget Agent
      4. Route Agent
      5. Parallel: Food Agent + Hotel Agent
      6. Budget Agent: validate
      7. If over budget → Route Agent replan (max 2 attempts)
      8. Generate health alerts + preference compliance notes
      9. Return final plan
    """

    def __init__(self):
        self.pref_agent = PreferenceAgent()
        self.attr_agent = AttractionsAgent()
        self.route_agent = RouteAgent()
        self.budget_agent = BudgetAgent()
        self.food_agent = FoodAgent()
        self.hotel_agent = HotelAgent()
        self.metrics = get_metrics_service()

    async def plan(self, user_id: str, session_id: str, message: str) -> Dict[str, Any]:
        """Main planning entry point."""
        t0 = time.time()
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        agent_trace = {"agents": [], "invocation_order": [], "durations_ms": [], "errors": []}

        async def trace(agent_name: str, coro):
            """Wrapper to time agent calls."""
            agent_trace["agents"].append(agent_name)
            agent_trace["invocation_order"].append(len(agent_trace["agents"]))
            t = time.time()
            try:
                result = await coro
                agent_trace["durations_ms"].append(int((time.time() - t) * 1000))
                return result
            except Exception as e:
                agent_trace["durations_ms"].append(int((time.time() - t) * 1000))
                agent_trace["errors"].append({"agent": agent_name, "error": str(e)})
                raise

        # Step 1: Parse intent
        intent = parse_travel_intent(message)
        city, days, budget, season = intent["city"], intent["days"], intent["budget"], intent["season"]

        # Step 2: Parse and update preferences
        pref_result = await trace("Preference Agent",
            self.pref_agent.parse_and_update(user_id, message))
        preferences = await self.pref_agent.get_preference(user_id)

        # Step 3: Parallel - Attractions + Budget
        attr_result = await trace("Attractions Agent",
            self.attr_agent.search(city, days, season, preferences))
        budget_result = await trace("Budget Agent",
            self.budget_agent.calculate(days, preferences.get("spending_style", "适中")))

        attractions = attr_result.get("attractions", [])

        # Step 4: Route planning
        route_result = await trace("Route Agent",
            self.route_agent.plan(attractions, {
                "days": days,
                "budget_limit": budget,
                "mobility_limitations": preferences.get("health", []),
                "preferred_start_time": "09:00",
                "transport_preferences": ["地铁", "公交", "出租车"],
                "replan_context": None
            }))

        # Step 5: Parallel - Food + Hotel
        food_result = await trace("Food Agent",
            self.food_agent.recommend(city, "", budget / days / 3))
        hotel_result = await trace("Hotel Agent",
            self.hotel_agent.search(city, budget / days, ""))

        # Step 6: Budget validation
        hotel_info = hotel_result.get("hotels", [{}])[0] if hotel_result.get("hotels") else {}
        hotel_cost = (hotel_info.get("price_per_night", 0) or 0) * days
        plan_summary = {
            "daily_routes": route_result.get("daily_routes", []),
            "hotel": {"name": hotel_info.get("name", ""), "total_cost": hotel_cost},
            "transport_to_city": {"type": "高铁", "cost": 220},  # mock: inbound transport
            "attractions_total": sum(a.get("ticket_price", 0) for a in attractions),
            "food_total": len(food_result.get("restaurants", [])) * (budget // days // 3),
            "transport_within_city": days * 30,  # estimated city transport
        }

        budget_check = await trace("Budget Agent (validation)",
            self.budget_agent.check_plan(budget, plan_summary))

        # Step 7: Budget → Route adjustment loop (max 2 attempts)
        if not budget_check["within_budget"] and budget_check["alerts"]:
            for attempt in [1, 2]:
                route_result = await self.route_agent.plan(attractions, {
                    "days": days,
                    "budget_limit": budget,
                    "mobility_limitations": preferences.get("health", []),
                    "preferred_start_time": "09:00",
                    "transport_preferences": ["地铁", "公交", "出租车"],
                    "replan_context": {
                        "mode": "replan", "reason": "over_budget",
                        "current_plan": route_result.get("daily_routes", []),
                        "budget_limit": budget, "attempt": attempt
                    }
                })
                plan_summary["daily_routes"] = route_result.get("daily_routes", [])
                budget_check = await self.budget_agent.check_plan(budget, plan_summary)
                if budget_check["within_budget"]:
                    break

        # Step 8: Generate health alerts and preference compliance
        health_alerts = self._generate_health_alerts(preferences)
        preference_compliance = self._generate_compliance(preferences)

        # Save to short-term memory
        short_mem = get_short_term_memory(session_id)
        short_mem.save_context(
            {"input": message},
            {"output": f"已为您规划{city}{days}天行程，预算{budget}元"}
        )

        total_ms = int((time.time() - t0) * 1000)
        self.metrics.increment("chat_requests_total")
        self.metrics.record_latency("chat", total_ms)

        # Compute reserve = total_budget - sum(category_costs)
        total_cost = (
            plan_summary["attractions_total"]
            + plan_summary["food_total"]
            + hotel_cost
            + plan_summary["transport_to_city"]["cost"]
            + plan_summary["transport_within_city"]
        )
        reserve = budget - total_cost

        # Get category breakdowns from budget_result
        cat_breakdown = budget_result  # from calculate_budget call

        return {
            "plan_id": plan_id,
            "city": city,
            "days": days,
            "budget": budget,
            "daily_routes": route_result.get("daily_routes", []),
            "attractions": attractions,
            "food": food_result.get("restaurants", []),
            "hotels": hotel_result.get("hotels", []),
            "budget_summary": {
                "total_budget": budget,
                "attractions_total": plan_summary["attractions_total"],
                "food_total": plan_summary["food_total"],
                "hotel_total": hotel_cost,
                "transport_total": plan_summary["transport_to_city"]["cost"] + plan_summary["transport_within_city"],
                "reserve": max(0, reserve),
                "within_budget": budget_check["within_budget"],
                "remaining": budget_check.get("remaining", 0),
                "alerts": budget_check.get("alerts", [])
            },
            "health_alerts": health_alerts,
            "preference_compliance": preference_compliance,
            "agent_trace": agent_trace,
        }

    def _generate_health_alerts(self, preferences: Dict[str, Any]) -> List[str]:
        alerts = []
        for condition, alert_text in _HEALTH_ALERT_RULES.items():
            if condition in preferences.get("health", []):
                alerts.append(alert_text)
        # Fallback for unlisted health conditions
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