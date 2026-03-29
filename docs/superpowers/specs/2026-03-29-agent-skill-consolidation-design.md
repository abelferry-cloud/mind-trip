# Agent & Skill 整合设计文档

**日期**: 2026-03-29
**状态**: Draft
**目标**: 将 7 个 Agent 整合为 3 个，集成 Tavily + 高德地图 Skill

---

## 1. 背景与目标

当前系统有 7 个独立 Agent（PlanningAgent, PreferenceAgent, AttractionsAgent, BudgetAgent, RouteAgent, FoodAgent, HotelAgent），每个 Agent 对应独立的工具层。

引入 Tavily（网络搜索）和高德地图（POI搜索 + 路线规划）两个 Skill 后，发现：
- 高德地图的 `search_poi()` 可覆盖景点、餐厅、酒店搜索
- 高德地图的 `driving_route()` / `walking_route()` / `transit_route()` 可覆盖路线规划
- Tavily 可提供实时网络信息补充

**整合目标**：
1. 集成 Tavily + 高德地图 Skill 到工具层
2. 将 7 个 Agent 合并为 3 个核心 Agent

---

## 2. Agent 整合方案

### 2.1 保留的 Agent（3个）

| Agent | 职责 | 备注 |
|-------|------|------|
| **PlanningAgent** | 主管，协调整个流程 | 不变 |
| **PreferenceAgent** | 唯一可写长期记忆的 Agent | 不变 |
| **BudgetAgent** | 预算计算与验证 | 不变（业务逻辑重要） |
| **~~AttractionsAgent~~** | → 合并入 TravelPlannerAgent | 删除 |
| **~~FoodAgent~~** | → 合并入 TravelPlannerAgent | 删除 |
| **~~HotelAgent~~** | → 合并入 TravelPlannerAgent | 删除 |
| **~~RouteAgent~~** | → 合并入 TravelPlannerAgent | 删除 |
| **~~SearchAgent~~** | → 合并入 TravelPlannerAgent | 删除 |

### 2.2 新增 Agent

**TravelPlannerAgent**（搜索规划 Agent）

职责：
- 使用高德地图 Skill 搜索景点、餐厅、酒店
- 使用高德地图 Skill 进行路线规划
- 使用 Tavily Skill 进行补充搜索
- 根据用户偏好（健康、预算）过滤结果

---

## 3. Skill 集成方案

### 3.1 API Key 配置

```env
# .env 新增
TAVILY_API_KEY=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
AMAP_API_KEY=25d103f72d4f260f9511e6099f1c3c8b
```

### 3.2 工具层设计

新建 `app/tools/travel_skills.py`：

```python
"""Travel Skills - 封装 Tavily + 高德地图为 LangChain Tool"""
from langchain_core.tools import tool
from app.skills.smart_map_guide.scripts.map_manager import MapManager
from app.skills.tavily.scripts.tavily_search import tavily_search

# 初始化 MapManager（单例）
_map_manager: MapManager | None = None

def get_map_manager() -> MapManager:
    global _map_manager
    if _map_manager is None:
        from app.config import settings
        _map_manager = MapManager(settings.amap_api_key)
    return _map_manager

@tool
def search_attractions(city: str, page_size: int = 20) -> list[dict]:
    """搜索城市景点（风景名胜 + 博物馆）"""
    mgr = get_map_manager()
    result = mgr.search_attractions(city, page_size)
    pois = result.get("pois", [])
    return [{"name": p["name"], "address": p.get("address", ""),
             "type": p.get("type", ""), "location": p.get("location", "")} for p in pois]

@tool
def search_restaurants(city: str, cuisine: str = "", page_size: int = 20) -> list[dict]:
    """搜索城市餐厅"""
    mgr = get_map_manager()
    result = mgr.search_restaurants(city, page_size)
    pois = result.get("pois", [])
    filtered = [p for p in pois if cuisine in p.get("type", "")] if cuisine else pois
    return [{"name": p["name"], "address": p.get("address", ""),
             "type": p.get("type", ""), "location": p.get("location", "")} for p in filtered]

@tool
def search_hotels(city: str, budget: float = 500.0, page_size: int = 20) -> list[dict]:
    """搜索城市酒店（按预算过滤）"""
    mgr = get_map_manager()
    # 使用 POI 搜索住宿类型
    result = mgr.search_poi(keywords="酒店", city=city, types="100000", page_size=page_size)
    pois = result.get("pois", [])
    # 简单按名称过滤（实际应解析价格字段）
    return [{"name": p["name"], "address": p.get("address", ""),
             "location": p.get("location", "")} for p in pois]

@tool
def plan_driving_route(origin: str, destination: str, city: str = "") -> dict:
    """驾车路线规划"""
    mgr = get_map_manager()
    result = mgr.driving_route(origin, destination, origin_city=city, dest_city=city)
    return {
        "distance_km": result["route"]["paths"][0]["distance"] / 1000,
        "duration_min": int(result["route"]["paths"][0]["cost"]["duration"] / 60),
        "tolls": result["route"]["paths"][0]["cost"].get("tolls", "0")
    }

@tool
def tavily_web_search(query: str, max_results: int = 5) -> dict:
    """Tavily 网络搜索（用于补充信息）"""
    result = tavily_search(
        query=query,
        max_results=max_results,
        include_answer=False,
        search_depth="basic"
    )
    return {"results": result.get("results", []), "answer": result.get("answer")}
```

### 3.3 旧工具层处理

- `app/tools/attractions_tools.py` → 保留作为 fallback，内部调用 `travel_skills`
- `app/tools/food_tools.py` → 同上
- `app/tools/hotel_tools.py` → 同上
- `app/tools/route_tools.py` → 同上
- `app/tools/search_tools.py` → 内部调用 `travel_skills`

---

## 4. TravelPlannerAgent 实现

```python
# app/agents/travel_planner.py
"""TravelPlannerAgent - 统一的搜索规划 Agent（合并版）"""
from typing import Any, Dict, List
from app.tools.travel_skills import (
    search_attractions, search_restaurants,
    search_hotels, plan_driving_route, tavily_web_search
)

class TravelPlannerAgent:
    """整合搜索 + 规划的 Agent

    替代原有的：AttractionsAgent, FoodAgent, HotelAgent, RouteAgent, SearchAgent
    """

    async def search_all(self, city: str, days: int, budget: float, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """一次性搜索景点、餐厅、酒店"""
        # 景点搜索
        attractions = search_attractions.invoke({"city": city, "page_size": 20})

        # 健康过滤
        health = preferences.get("health", [])
        if any(h in health for h in ["心脏病", "高血压", "哮喘"]):
            attractions = [a for a in attractions if "高强度" not in a.get("name", "")]

        # 餐厅搜索
        restaurants = search_restaurants.invoke({"city": city, "page_size": 20})

        # 酒店搜索
        hotels = search_hotels.invoke({"city": city, "budget": budget / days, "page_size": 10})

        return {
            "attractions": attractions,
            "restaurants": restaurants,
            "hotels": hotels
        }

    async def plan_routes(self, attractions: List[dict], constraints: Dict[str, Any]) -> Dict[str, Any]:
        """规划每日路线"""
        days = constraints.get("days", 1)
        city = constraints.get("city", "")

        routes = []
        for i, attr in enumerate(attractions[:days]):
            route = plan_driving_route.invoke({
                "origin": "酒店",
                "destination": attr["name"],
                "city": city
            })
            routes.append({
                "day": i + 1,
                "attraction": attr["name"],
                "distance_km": route["distance_km"],
                "duration_min": route["duration_min"]
            })
        return {"routes": routes}
```

---

## 5. Supervisor 协调流程（更新后）

```
PlanningAgent.plan()
    │
    ├─► PreferenceAgent.parse_and_update()  # 解析偏好
    │
    ├─► BudgetAgent.calculate()              # 计算预算
    │
    ├─► TravelPlannerAgent.search_all()     # 并行搜索景点/餐厅/酒店 ← 合并
    │
    ├─► TravelPlannerAgent.plan_routes()    # 规划路线 ← 合并
    │
    ├─► BudgetAgent.check_plan()            # 验证预算
    │
    └─► 生成健康提醒 + 偏好合规说明
```

---

## 6. 文件变更清单

### 新建
- `app/tools/travel_skills.py` - Skill 封装层
- `app/agents/travel_planner.py` - 合并后的 TravelPlannerAgent

### 修改
- `app/config.py` - 添加 `tavily_api_key`, `amap_api_key`
- `.env` - 添加 API Key 配置
- `app/agents/supervisor.py` - 更新协调流程，引入 TravelPlannerAgent
- `app/agents/__init__.py` - 导出变更

### 删除
- `app/agents/attractions.py` - 合并入 TravelPlannerAgent
- `app/agents/food.py` - 合并入 TravelPlannerAgent
- `app/agents/hotel.py` - 合并入 TravelPlannerAgent
- `app/agents/route.py` - 合并入 TravelPlannerAgent
- `app/agents/search.py` - 合并入 TravelPlannerAgent

---

## 7. 风险与注意事项

1. **API Key 安全**: API Key 不要提交到 git，确保 `.env` 在 `.gitignore` 中
2. **POI 价格字段**: 高德地图 POI 返回的价格字段需验证，部分场景可能需要 Tavily 补充
3. **预算重试逻辑**: 原 RouteAgent 的重试逻辑（最多2次）需迁移到 TravelPlannerAgent
4. **健康过滤**: 目前过滤是简单字符串匹配，后续可优化为解析 intensity 字段
