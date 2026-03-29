# Agent 精简 + 工具升级设计

**日期**: 2026-03-29
**状态**: 已批准
**版本**: v1.0

---

## 1. 背景与目标

当前项目有 7 个 Agent（1 个主管 + 6 个专家），所有工具均使用硬编码 mock 数据，未连接真实 API。用户已提供两个真实数据源 SKILL：

- **Tavily** — Web 搜索（`app/skills/tavily`）
- **高德地图** — POI 搜索 + 路线规划（`app/skills/smart_map_guide`）

**目标**：
1. 整合 Tavily + 高德地图，替换所有 mock 数据
2. 精简 Agent 数量，从 7 个减少到 4 个
3. API Key 统一通过 `.env` 环境变量注入

---

## 2. 架构变化

### Before（7 个 Agent）

```
PlanningAgent → AttractionsAgent
             → BudgetAgent
             → FoodAgent
             → HotelAgent
             → RouteAgent
             → PreferenceAgent
```

### After（4 个 Agent）

```
PlanningAgent → SearchAgent (Tavily + 高德地图)
             → BudgetAgent
             → PreferenceAgent
```

---

## 3. Agent 职责

### PlanningAgent（不变）

主管 Agent，负责协调流程、意图解析、最终响应组装。

### SearchAgent（新增）

统一封装 Tavily + 高德地图，对外暴露单一搜索接口：

| 方法 | 底层调用 | 用途 |
|------|---------|------|
| `search_attractions(city, days, season, preferences)` | 高德地图 `attractions` + Tavily 补充 | 景点搜索 |
| `search_restaurants(city, style, budget_per_meal)` | 高德地图 `restaurants` + Tavily 补充 | 餐厅/美食 |
| `search_hotels(city, budget, location)` | 高德地图 `search(POItype=酒店)` + Tavily 补充 | 酒店搜索 |
| `plan_route(attractions, constraints)` | 高德地图 `driving/walking/transit` | 路线规划 |

### BudgetAgent（保留）

负责预算计算和验证，逻辑独立，不依赖搜索结果。

### PreferenceAgent（保留）

唯一可写入长期记忆的 Agent，职责不变。

---

## 4. 协调流程

```
1. 解析意图（PlanningAgent 内：城市、天数、预算、季节）
2. PreferenceAgent.parse_and_update() — 解析并更新偏好
3. 并行执行：
   - SearchAgent.search_attractions()
   - BudgetAgent.calculate()
4. SearchAgent.plan_route() — 高德地图路线规划
5. 并行执行：
   - SearchAgent.search_restaurants()
   - SearchAgent.search_hotels()
6. BudgetAgent.check_plan() — 预算验证
7. 如超预算 → SearchAgent.plan_route(简化版)，最多 2 次重试
8. 生成健康提醒 + 偏好合规
9. 组装响应
```

---

## 5. 工具层改造

### 新建文件

- `app/tools/search_tools.py` — 封装 Tavily + 高德地图 API 调用
  - `tavily_search()` — Tavily 通用搜索
  - `amap_attractions()` — 高德地图景点 POI 搜索
  - `amap_restaurants()` — 高德地图餐厅 POI 搜索
  - `amap_hotels()` — 高德地图酒店 POI 搜索
  - `amap_route()` — 高德地图路线规划

### 删除文件（mock 数据）

- `app/tools/attractions_tools.py`
- `app/tools/food_tools.py`
- `app/tools/hotel_tools.py`
- `app/tools/route_tools.py`

### 保留文件

- `app/tools/budget_tools.py` — 预算逻辑独立保留

---

## 6. API Key 配置

所有第三方 Key 通过 `.env` 环境变量注入：

```env
# .env
TAVILY_API_KEY=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
AMAP_API_KEY=25d103f72d4f260f9511e6099f1c3c8b
```

`app/config.py` 添加对应字段：
- `tavily_api_key: str`
- `amap_api_key: str`

---

## 7. 错误处理

- 高德地图 API 失败 → 回退到 Tavily 搜索
- Tavily API 失败 → 回退到 mock 数据（保留最小可用性）
- 两个都失败 → 返回错误信息，不阻塞流程

---

## 8. 文件变更清单

| 操作 | 文件 |
|------|------|
| 新建 | `app/tools/search_tools.py` |
| 新建 | `app/agents/search.py` |
| 修改 | `app/agents/supervisor.py` |
| 修改 | `app/tools/__init__.py` |
| 修改 | `app/config.py` |
| 修改 | `.env`（添加 API Key） |
| 删除 | `app/tools/attractions_tools.py` |
| 删除 | `app/tools/food_tools.py` |
| 删除 | `app/tools/hotel_tools.py` |
| 删除 | `app/tools/route_tools.py` |

---

## 9. 测试策略

- `search_tools.py` 各方法独立测试（mock 外部 API 响应）
- SearchAgent 方法级测试
- PlanningAgent 端到端集成测试（使用真实 API 或充分 mock）
