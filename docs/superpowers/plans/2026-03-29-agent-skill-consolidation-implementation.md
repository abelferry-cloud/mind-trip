# Agent & Skill 整合实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 7 个 Agent 合并为 3 个，并集成 Tavily + 高德地图 Skill 到工具层

**Architecture:** 新建 `travel_skills.py` 封装 SKILL 为 LangChain Tool，新建 `TravelPlannerAgent` 替代 5 个旧 Agent，更新 `supervisor.py` 协调流程

**Tech Stack:** LangChain Core Tools, Tavily API, 高德地图 API, Python async/await

**Reference Spec:** `docs/superpowers/specs/2026-03-29-agent-skill-consolidation-design.md`

---

## 文件结构

```
app/tools/travel_skills.py          # [新建] Skill 封装层
app/agents/travel_planner.py        # [新建] 合并后的 Agent
app/agents/supervisor.py           # [修改] 更新协调流程
app/agents/__init__.py             # [修改] 导出 TravelPlannerAgent
app/tools/attractions_tools.py      # [修改] 内部调用 travel_skills
app/tools/food_tools.py            # [修改] 内部调用 travel_skills
app/tools/hotel_tools.py           # [修改] 内部调用 travel_skills
app/tools/route_tools.py           # [修改] 内部调用 travel_skills
app/tools/search_tools.py           # [修改] 内部调用 travel_skills
app/agents/attractions.py           # [删除] 合并入 TravelPlannerAgent
app/agents/food.py                 # [删除] 合并入 TravelPlannerAgent
app/agents/hotel.py                # [删除] 合并入 TravelPlannerAgent
app/agents/route.py                # [删除] 合并入 TravelPlannerAgent
app/agents/search.py               # [删除] 合并入 TravelPlannerAgent
app/skills/smart_map_guide/scripts/config.json  # [修改] 添加 API Key
```

---

## Task 1: 创建 `travel_skills.py`（Skill 封装层）

**Files:**
- Create: `app/tools/travel_skills.py`
- Reference: `app/skills/smart_map_guide/scripts/map_manager.py`, `app/skills/tavily/scripts/tavily_search.py`

- [ ] **Step 1: 创建 `app/tools/travel_skills.py`**

```python
"""Travel Skills - 封装 Tavily + 高德地图为 LangChain Tool"""
from typing import Annotated, List
from langchain_core.tools import tool
from app.skills.smart_map_guide.scripts.map_manager import MapManager
from app.skills.tavily.scripts.tavily_search import tavily_search

_map_manager: MapManager | None = None


def get_map_manager() -> MapManager:
    global _map_manager
    if _map_manager is None:
        from app.config import get_settings
        settings = get_settings()
        _map_manager = MapManager(settings.amap_api_key)
    return _map_manager


@tool
def search_attractions(city: Annotated[str, "城市名称"]) -> Annotated[List[dict], "景点列表"]:
    """搜索城市景点（风景名胜 + 博物馆）"""
    mgr = get_map_manager()
    result = mgr.search_attractions(city, page_size=20)
    pois = result.get("pois", [])
    return [
        {
            "name": p.get("name", ""),
            "address": p.get("address", ""),
            "type": p.get("type", ""),
            "location": p.get("location", ""),
            "intensity": _infer_intensity(p.get("name", ""), p.get("type", "")),
        }
        for p in pois
    ]


@tool
def search_restaurants(
    city: Annotated[str, "城市名称"],
    cuisine: Annotated[str, "菜系类型（可选）"] = "",
) -> Annotated[List[dict], "餐厅列表"]:
    """搜索城市餐厅（排除快餐）"""
    mgr = get_map_manager()
    result = mgr.search_restaurants(city, page_size=20)
    pois = result.get("pois", [])
    if cuisine:
        pois = [p for p in pois if cuisine in p.get("type", "")]
    return [
        {
            "name": p.get("name", ""),
            "address": p.get("address", ""),
            "type": p.get("type", ""),
            "location": p.get("location", ""),
        }
        for p in pois
    ]


@tool
def search_hotels(
    city: Annotated[str, "城市名称"],
    budget: Annotated[float, "每晚预算"] = 500.0,
    location: Annotated[str, "位置偏好（可选）"] = "",
) -> Annotated[List[dict], "酒店列表"]:
    """搜索城市酒店"""
    mgr = get_map_manager()
    result = mgr.search_poi(keywords="酒店", city=city, types="100000", page_size=20)
    pois = result.get("pois", [])
    if location:
        pois = [p for p in pois if location in p.get("address", "")]
    return [
        {
            "name": p.get("name", ""),
            "address": p.get("address", ""),
            "location": p.get("location", ""),
        }
        for p in pois
    ]


@tool
def plan_driving_route(
    origin: Annotated[str, "起点地址或坐标"],
    destination: Annotated[str, "终点地址或坐标"],
    city: Annotated[str, "城市名称（用于地理编码）"] = "",
) -> Annotated[dict, "路线规划结果"]:
    """驾车路线规划（高德地图）"""
    mgr = get_map_manager()
    result = mgr.driving_route(origin, destination, origin_city=city, dest_city=city)
    path = result["route"]["paths"][0]
    return {
        "distance_km": round(float(path.get("distance", 0)) / 1000, 1),
        "duration_min": int(int(path["cost"]["duration"]) / 60),
        "tolls": path["cost"].get("tolls", "0"),
        "origin_name": result.get("origin_name", origin),
        "dest_name": result.get("dest_name", destination),
    }


@tool
def plan_walking_route(
    origin: Annotated[str, "起点地址或坐标"],
    destination: Annotated[str, "终点地址或坐标"],
    city: Annotated[str, "城市名称"] = "",
) -> Annotated[dict, "步行路线结果"]:
    """步行路线规划（高德地图）"""
    mgr = get_map_manager()
    result = mgr.walking_route(origin, destination, origin_city=city, dest_city=city)
    path = result["route"]["paths"][0]
    return {
        "distance_km": round(float(path.get("distance", 0)) / 1000, 1),
        "duration_min": int(int(path["cost"]["duration"]) / 60),
    }


@tool
def tavily_web_search(
    query: Annotated[str, "搜索查询"],
    max_results: Annotated[int, "最大结果数"] = 5,
) -> Annotated[dict, "搜索结果"]:
    """Tavily 网络搜索（用于补充实时信息）"""
    result = tavily_search(
        query=query,
        max_results=max_results,
        include_answer=False,
        search_depth="basic",
    )
    return {
        "results": result.get("results", []),
        "answer": result.get("answer"),
    }


def _infer_intensity(name: str, ptype: str) -> str:
    """根据名称和类型推断体力消耗强度"""
    high_keywords = ["登山", "徒步", "攀岩", "探险", "极限"]
    medium_keywords = ["观光", "博物馆", "寺庙", "古镇"]
    if any(k in name for k in high_keywords) or "high" in ptype.lower():
        return "high"
    if any(k in name for k in medium_keywords):
        return "medium"
    return "low"
```

- [ ] **Step 2: 验证 import**

Run: `python -c "from app.tools.travel_skills import search_attractions, search_restaurants, search_hotels, plan_driving_route, tavily_web_search; print('OK')"`
Expected: 输出 `OK`（无 ImportError）

- [ ] **Step 3: 提交**

---

## Task 2: 创建 `TravelPlannerAgent`

**Files:**
- Create: `app/agents/travel_planner.py`
- Reference: `app/tools/travel_skills.py`

- [ ] **Step 1: 创建 `app/agents/travel_planner.py`**

```python
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
```

- [ ] **Step 2: 验证语法**

Run: `python -c "from app.agents.travel_planner import TravelPlannerAgent; print('OK')"`

- [ ] **Step 3: 提交**

---

## Task 3: 更新 `supervisor.py` 引入 TravelPlannerAgent

**Files:**
- Modify: `app/agents/supervisor.py`

**变更点：**
1. Import 区：去掉 `AttractionsAgent, RouteAgent, FoodAgent, HotelAgent`，改为 `TravelPlannerAgent`
2. `__init__` 方法：替换 5 个 Agent 实例为 `self.travel_agent = TravelPlannerAgent()`
3. `plan()` 方法：更新协调流程，第3步并行改为 `TravelPlannerAgent.search_all()` + `BudgetAgent.calculate()`，第4步路线规划改为 `TravelPlannerAgent.plan_routes()`

- [ ] **Step 1: 更新 import**

```
# 旧
from app.agents.preference import PreferenceAgent
from app.agents.attractions import AttractionsAgent
from app.agents.route import RouteAgent
from app.agents.budget import BudgetAgent
from app.agents.food import FoodAgent
from app.agents.hotel import HotelAgent

# 新
from app.agents.preference import PreferenceAgent
from app.agents.budget import BudgetAgent
from app.agents.travel_planner import TravelPlannerAgent
```

- [ ] **Step 2: 更新 __init__**

```
# 旧
self.pref_agent = PreferenceAgent()
self.attr_agent = AttractionsAgent()
self.route_agent = RouteAgent()
self.budget_agent = BudgetAgent()
self.food_agent = FoodAgent()
self.hotel_agent = HotelAgent()

# 新
self.pref_agent = PreferenceAgent()
self.budget_agent = BudgetAgent()
self.travel_agent = TravelPlannerAgent()
```

- [ ] **Step 3: 更新 plan() 协调流程**

原流程第3步并行：
```python
# 旧
attr_result, budget_result = await asyncio.gather(
    trace("Attractions Agent", self.attr_agent.search(city, days, season, preferences)),
    trace("Budget Agent", self.budget_agent.calculate(days, preferences.get("spending_style", "适中")))
)
# ...后续 food/hotel separate agents

# 新
search_result, budget_result = await asyncio.gather(
    trace("TravelPlanner Agent (search)", self.travel_agent.search_all(city, days, budget, preferences)),
    trace("Budget Agent", self.budget_agent.calculate(days, preferences.get("spending_style", "适中")))
)
attractions = search_result.get("attractions", [])
restaurants = search_result.get("restaurants", [])
hotels = search_result.get("hotels", [])
```

原流程第4步路线：
```python
# 旧
route_result = await trace("Route Agent", self.route_agent.plan(attractions, {...}))

# 新
route_result = await trace("TravelPlanner Agent (route)",
    self.travel_agent.plan_routes(attractions, {
        "days": days,
        "city": city,
        "preferred_start_time": "09:00",
    }))
```

- [ ] **Step 4: 验证语法**

Run: `python -c "from app.agents.supervisor import PlanningAgent; print('OK')"`

- [ ] **Step 5: 提交**

---

## Task 4: 更新旧工具层（fallback 兼容）

**Files:**
- Modify: `app/tools/attractions_tools.py`, `app/tools/food_tools.py`, `app/tools/hotel_tools.py`, `app/tools/route_tools.py`, `app/tools/search_tools.py`

每个旧工具文件改为从 `travel_skills` import 并委托调用。

- [ ] **Step 1: 更新每个工具文件**

- [ ] **Step 2: 验证无 import 错误**

Run: `python -c "from app.tools import attractions_tools, food_tools, hotel_tools, route_tools, search_tools; print('OK')"`

- [ ] **Step 3: 提交**

---

## Task 5: 删除废弃的 Agent 文件

**Files:**
- Delete: `app/agents/attractions.py`, `app/agents/food.py`, `app/agents/hotel.py`, `app/agents/route.py`, `app/agents/search.py`

- [ ] **Step 1: 删除文件**

- [ ] **Step 2: 验证无 import 错误**

Run: `python -c "from app.agents.supervisor import PlanningAgent; from app.agents.travel_planner import TravelPlannerAgent; print('OK')"`

- [ ] **Step 3: 提交**

---

## Task 6: 更新 `__init__.py` 导出

**Files:**
- Modify: `app/agents/__init__.py`

```python
from app.agents.supervisor import PlanningAgent
from app.agents.preference import PreferenceAgent
from app.agents.budget import BudgetAgent
from app.agents.travel_planner import TravelPlannerAgent

__all__ = ["PlanningAgent", "PreferenceAgent", "BudgetAgent", "TravelPlannerAgent"]
```

- [ ] **Step 1: 更新导出**

- [ ] **Step 2: 验证**

Run: `python -c "from app.agents import PlanningAgent, PreferenceAgent, BudgetAgent, TravelPlannerAgent; print('OK')"`

- [ ] **Step 3: 提交**

---

## Task 7: 更新高德地图 SKILL 配置文件

**Files:**
- Modify: `app/skills/smart_map_guide/scripts/config.json`

```json
{
  "amap_key": "25d103f72d4f260f9511e6099f1c3c8b"
}
```

- [ ] **Step 1: 更新 config.json**

- [ ] **Step 2: 提交**

---

## Task 8: 最终验证

- [ ] **Step 1: 启动应用验证无报错**

Run: `python -m app.main`

- [ ] **Step 2: 测试 chat 接口（可选，如服务可启动）**

Run: `curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{"message": "我想去北京3天预算5000元", "user_id": "test"}'`
