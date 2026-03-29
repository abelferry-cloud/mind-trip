# 出行规划 Multi-Agent 系统设计文档

> 日期：2026-03-27
> 目标：基于 LangChain 实现工业级单目的地出行规划 Multi-Agent 系统，作为 AI 应用开发方向的求职作品

---

## 1. 项目定位

### 1.1 核心价值

通过对话式交互，用户输入出行意图（目的地、天数、预算、偏好），系统输出完整的单目的地深度游行程规划方案。

### 1.2 场景范围

- 单目的地深度游（如"杭州3天"、"成都4天"）
- 覆盖：景点推荐、路线规划、预算控制、美食推荐、住宿推荐、偏好管理
- 展示重点：Multi-Agent 协作、记忆管理、工程化架构、监控容错

### 1.3 技术栈

| 层级 | 技术选型 | 选型理由 |
|------|---------|---------|
| Web 框架 | FastAPI + Uvicorn | 异步原生支持，并发能力强 |
| Agent 框架 | LangChain / LangGraph | 生态成熟，Tool Calling 支持好 |
| 模型 | OpenAI GPT / Claude（可切换） | 通用推理能力强 |
| 短期记忆 | LangChain Memory (ConversationBuffer) | 与框架深度集成 |
| 长期记忆 | SQLite | 轻量、免运维、面试可解释 |
| 监控 | Prometheus Metrics + 结构化日志 | 工业标准，可观测性强 |

---

## 2. Multi-Agent 架构

### 2.1 协作模式：Supervisor + Specialist

采用星型 Supervisor 模式，以 Planning Agent 为总控，分发给专业子 Agent。

**协作拓扑说明**：虽然所有子 Agent 都在 Planning Agent 管辖下，但调用顺序有依赖关系（见 2.3）。

```
┌──────────────────────────────────────────────────────┐
│                     User Input                        │
│           "我去杭州3天，预算5000"                      │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  Planning Agent │  ← Supervisor（总控）
              │  (Supervisor)   │
              └────────┬────────┘
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │Attractions│  │  Route   │  │  Budget  │
  │  Agent    │  │  Agent   │  │  Agent   │
  └──────────┘  └──────────┘  └──────────┘
        │              │              │
        ▼              ▼              ▼
  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │   Food    │  │  Hotel   │  │Preference│
  │  Agent    │  │  Agent   │  │  Agent   │
  └──────────┘  └──────────┘  └──────────┘
        ↑              │              │
        └──────────────┴──────────────┘
              Budget → Route 调整循环
              （超支时触发，最多2次）
```

### 2.2 Agent 职责

| Agent | 职责 | Tool Calling 能力 |
|-------|------|------------------|
| **Planning Agent** | 意图解析、任务分解、子Agent调度、结果整合 | 协调所有子Agent |
| **Attractions Agent** | 景点搜索、评分、季节适宜度、预约难度 | search_attractions, get_attraction_detail |
| **Route Agent** | 每日行程规划、时长估算、最优顺序 | plan_daily_route, estimate_travel_time |
| **Budget Agent** | 预算分配、性价比判断、超支预警 | calculate_budget, check_budget_vs_plan |
| **Food Agent** | 本地特色美食、价位、位置推荐 | recommend_restaurants |
| **Hotel Agent** | 住宿位置、价格、评价推荐 | search_hotels |
| **Preference Agent** | 用户偏好读写（禁忌、消费习惯、身体条件） | update_preference, get_preference |

### 2.3 Agent 协作流程

```
用户: "我要去杭州3天，预算5000，不喜欢硬座，我有心脏病"

Planning Agent
  ├─ 解析：目的地=杭州，天数=3，预算=5000
  ├─ Preference Agent ←── 更新长期记忆（硬座禁忌 + 心脏病）
  │
  ├─ 并行调用:
  │     Attractions Agent ──→ 查询 Preference（心脏病患者需排除剧烈项目）
  │     Budget Agent ────────→ 初始化预算框架
  │
  ├─ Route Agent ─────────────→ 基于景点生成路线
  │
  ├─ 并行调用:
  │     Food Agent ───────────→ 补充美食推荐
  │     Hotel Agent ───────────→ 补充住宿推荐
  │
  ├─ Budget Agent ────────────→ 校验总花费，超支则触发 Route Agent 调整
  │
  └─ 整合输出:
       ├── 完整行程方案（每日景点 + 交通）
       ├── 预算明细
       ├── 健康提醒（"请随身携带药物"）
       └── 偏好合规说明（"已为您排除硬座选项"）
```

### 2.4 Preference Agent 的特殊地位

- **唯一写长期记忆的 Agent**：所有用户偏好（禁忌、消费习惯、身体条件）统一写入 SQLite
- **其他 Agent 只读**：Attractions/Route/Food/Hotel 等 Agent 在输出前查询 Preference Agent
- **主动提醒机制**：心脏病等医疗禁忌在最终方案中主动生成健康提醒，不只是静默过滤

**健康提醒生成规则（规则驱动，非 LLM 自由生成）**：

| 偏好条件 | 触发规则 | 生成提醒 |
|---------|---------|---------|
| `health` 包含 "心脏病" | 用户偏好含心脏病史 | "您的行程包含较多步行，建议随身携带日常药物并避免剧烈活动" |
| `health` 包含 "糖尿病" | 用户偏好含糖尿病 | "建议随身携带血糖仪和备用食物，注意按时用餐" |
| `hardships` 包含 "硬座" | 用户明确不喜硬座 | "已为您排除火车硬座选项，全程优先选择卧铺/座位" |
| `health` 含其他关键词 | 透传原始描述 | "请注意：{原始偏好描述}" |

健康提醒由 Planning Agent 在整合阶段查询 Preference Agent 并根据规则表生成，**不是 LLM 自由发挥**，确保提醒的可靠性。

---

## 3. 记忆系统

### 3.1 双层记忆架构

```
┌─────────────────────────────────────────────────────┐
│                   Memory Layer                        │
├──────────────────────┬──────────────────────────────┤
│   Short-Term Memory  │      Long-Term Memory          │
│   (Session Context)  │      (User Profile)           │
├──────────────────────┼──────────────────────────────┤
│  · 当前对话上下文     │  · 用户偏好（禁忌、消费习惯）│
│  · 进行中的行程规划   │  · 历史出行记录              │
│  · 本次Agent中间结果  │  · 反馈修正记录              │
│  · TTL: 单次会话     │  · TTL: 永久保留              │
└──────────────────────┴──────────────────────────────┘
```

### 3.2 短期记忆（Short-Term Memory）

- **实现**：LangChain `ConversationBufferMemory` 或 LangGraph 的 `MemorySaver`
- **内容**：用户输入序列、Agent 输出序列、会话状态（规划进度）
- **生命周期**：单次会话结束即清除

### 3.3 长期记忆（Long-Term Memory）

- **实现**：SQLite 数据库文件 `data/memory.db`
- **内容**：
  - `preferences` 表：`user_id`, `category`（hardships/health/spending_style/city_preferences）, `value`（**JSON 字符串**，如 `["硬座"]` 或 `"节省"`）, `updated_at`
    - 示例：`user_id=u1, category=health, value="[\"心脏病\"]", updated_at=2026-03-27`
  - `trip_history` 表：`user_id`, `city`, `days`, `plan_summary`（JSON 字符串）, `created_at`
  - `feedback` 表：`user_id`, `plan_id`, `feedback_text`, `created_at`
- **value 存储格式**：所有 preference value 均以 **JSON 字符串** 存储（数组或字符串），读取时解析为 Python 对象。`get_preference` 的嵌套返回格式（如 `{"hardships": ["硬座"], "health": ["心脏病"]}`）是读取时动态组装，而非存储格式。
- **生命周期**：永久保留，用户可更新
- **写权限约束**：通过 `app/services/memory_service.py` 提供统一访问接口，**仅 Preference Agent 调用写方法**，其他 Agent 仅调用读方法，从架构上保证单写原则（不能技术强防，但通过代码规范约束）。

### 3.4 记忆与 Agent 的读写关系

| Agent | 读长期记忆 | 写长期记忆 |
|-------|----------|----------|
| Preference Agent | ✓ | ✓（唯一写入方）|
| Planning Agent | ✓ | ✗ |
| Attractions Agent | ✓ | ✗ |
| Route Agent | ✓ | ✗ |
| Budget Agent | ✓ | ✗ |
| Food Agent | ✓ | ✗ |
| Hotel Agent | ✓ | ✗ |

---

## 4. 函数调用（Tools）设计

### 4.1 Attractions Tools

```python
search_attractions(city: str, days: int, season: str)
  → [{"id", "name", "score", "best_season", "price_range", "intensity", "tips"}]
  # intensity: "low" | "medium" | "high"，用于 Attractions Agent 过滤心脏病等高强度禁忌

get_attraction_detail(attraction_id: str)
  → {"id", "name", "open_hours", "ticket_price", "booking_difficulty", "intensity"}

check_availability(attraction_id: str, date: str)
  → {"available": true, "booking_tips": "建议提前2天预约", "crowd_level": "中等"}
  # date 格式：YYYY-MM-DD；返回 availability 仅供参考，非实时数据
```

### 4.2 Route Tools

```python
plan_daily_route(
  attractions: List[dict],        # search_attractions 返回的景点列表
  constraints: {
    "days": int,                  # 游玩天数
    "budget_limit": float,        # 每日预算上限
    "mobility_limitations": List[str],  # 行动限制（如"心脏病"→排除高强度景点）
    "preferred_start_time": str,   # 每日出发时间，如 "09:00"
    "transport_preferences": List[str], # 可用交通方式，如 ["公交", "地铁", "出租车"]
    "replan_context": dict | None,  # 调整模式上下文（见下方协议），首次规划时为 None
  }
)
  → [
      {
        "day": 1,
        "attractions": [{"id": "attr_001", "name": "西湖", "arrival_time": "09:30", "leave_time": "11:30"}],
        "transport": {"from": "酒店", "to": "西湖", "type": "地铁", "duration_minutes": 25},
        "meals": [{"type": "午餐", "restaurant": "外婆家", "budget": 80}]
      },
      ...
    ]

# Budget → Route 调整协议（replan_context 格式）：
replan_context: {
  "mode": "replan",
  "reason": "over_budget",        # "over_budget" | "preference_changed"
  "current_plan": {...},          # 当前路线 plan（上面同样的结构）
  "budget_limit": 5000,           # 本次不能超过的预算
  "attempt": 1                   # 当前调整轮次（1 或 2）
}
# Route Agent 收到 replan_context 时：
#   - attempt=1：优先减少非核心景点，保留核心景点
#   - attempt=2：仅保留最高优先级景点，返回最小可行路线

estimate_travel_time(from_location: str, to_location: str, transport: str)
  → {"duration_minutes": 45, "distance_km": 12}
```

### 4.3 Budget Tools

```python
calculate_budget(duration: int, style: str)
  → {"total_budget": 5000, "attractions_budget": 800, "food_budget": 1200, "hotel_budget": 1500, "transport_budget": 500, "reserve_budget": 500}

check_budget_vs_plan(budget: float, plan: dict)
  → {"within_budget": true, "remaining": 340, "alerts": []}
# plan 结构：
plan: {
  "daily_routes": [
    {
      "day": 1,
      "attractions": [{"id": "attr_001", "name": "西湖", "ticket_price": 0, "intensity": "low"}],
      "transport": {"type": "地铁", "estimated_cost": 20},
      "meals": [{"type": "午餐", "restaurant": "外婆家", "estimated_cost": 80}]
    }
  ],
  "hotel": {"name": "如家", "nights": 3, "total_cost": 450},
  "transport_to_city": {"type": "高铁", "cost": 220},
  "attractions_total": 320,
  "food_total": 600,
  "transport_within_city": 80
}
```

### 4.4 Preference Tools

```python
update_preference(user_id: str, key: str, value: Any)
  → {"success": true}

get_preference(user_id: str)
  → {"hardships": ["硬座"], "health": ["心脏病"], "spending_style": "节省"}
```

### 4.5 Food Tools

```python
recommend_restaurants(city: str, style: str, budget_per_meal: float)
  → [{"name", "cuisine", "price_level", "location", "signature_dishes"}]
```

### 4.6 Hotel Tools

```python
search_hotels(city: str, budget: float, location_preference: str)
  → [{"name", "price", "location", "rating", "nearby_attractions"}]
```

---

## 5. API 接口设计

### 5.1 核心接口

```
POST /api/chat
  Body: { "user_id": "u123", "message": "我要去杭州3天，预算5000", "session_id": "sess_abc" }
  Response: {
    "answer": "为您规划了杭州3天行程...",
    "plan_id": "plan_789",
    "agent_trace": {
      "agents": ["Planning Agent", "Attractions Agent", "Route Agent", "Budget Agent"],
      "invocation_order": [1, 2, 3, 4],
      "durations_ms": [120, 2100, 3500, 450],
      "errors": []
    },
    "health_alerts": ["您的行程包含较多步行，建议随身携带日常药物并避免剧烈活动"]
  }

GET  /api/plan/{plan_id}
  Response: {
    "plan_id": "plan_789",
    "city": "杭州",
    "days": 3,
    # agent_trace 不出现在 plan 响应中，仅在 /api/chat 的首次响应中返回
    "daily_routes": [...],
    "attractions": [...],
    "food": [...],
    "hotels": [...],
    "budget_summary": {...},
    "health_alerts": [...]
  }

GET  /api/preference/{user_id}
  Response: {
    "user_id": "u123",
    "preferences": {"hardships": ["硬座"], "health": ["心脏病"], ...},
    "history_trips": [...]
  }

PUT  /api/preference/{user_id}
  Body: { "key": "health", "value": "心脏病" }
  Response: { "success": true }

GET  /api/metrics
  Response: { "qps": 12.5, "latency_p50_ms": 850, "latency_p99_ms": 3200, "error_rate": 0.02 }

GET  /api/health
  Response: {
    "status": "healthy",
    "llm_available": true,    # true = 当前可用的模型数量 ≥ 1（至少一个模型可响应）；false = 所有模型均不可用
    "llm_primary_available": true,  # true = 主模型（OpenAI）可用；用于判断是否需要走降级链路
    "db_status": "connected"
  }
```

### 5.2 会话与用户标识

- `session_id`：关联短期记忆（LangChain Memory），每次新建对话生成
  - **匿名用户**：无 `user_id` 时，系统自动生成临时 `user_id`（如 `anon_<uuid>`），偏好不跨会话持久化
  - **多标签支持**：同一 `user_id` 可有多并发 `session_id`（多浏览器标签），各自独立短期记忆，长期记忆共享
- `user_id`：关联长期记忆（SQLite），持久化用户偏好
- `session_id` 不可跨会话恢复（重启服务后需重新创建）；`user_id` 永久有效

### 5.3 agent_trace 字段定义

```python
agent_trace: {
  "agents": ["Planning Agent", "Attractions Agent", "Route Agent", "Budget Agent"],
  "invocation_order": [1, 2, 3, 4],
  "durations_ms": [120, 2100, 3500, 450],
  "errors": []  # 如果某个 Agent 失败，记录错误信息
}
```

### 5.4 /api/plan/{plan_id} 响应完整 Schema

```python
{
  "plan_id": "plan_789",
  "city": "杭州",
  "days": 3,
  "daily_routes": [
    {
      "day": 1,
      "date": "2026-04-01",
      "attractions": [{"id": "attr_001", "name": "西湖", "arrival": "09:00", "leave": "11:30", "ticket_price": 0, "intensity": "low"}],
      "transport": {"from": "酒店", "to": "西湖", "type": "地铁", "duration_min": 25, "cost": 4},
      "meals": [{"type": "午餐", "restaurant": "外婆家", "budget": 80, "location": "西湖区"}]
    }
  ],
  "attractions": [{"id": "attr_001", "name": "西湖", "score": 4.8, "price_range": "0-50"}, ...],
  "food": [{"name": "外婆家", "cuisine": "浙菜", "price_level": "¥", "signature_dishes": ["东坡肉"]}, ...],
  "hotels": [{"name": "如家精选", "location": "西湖区", "price_per_night": 280, "rating": 4.5, "nearby_attractions": ["西湖", "灵隐寺"]}],
  "budget_summary": {
    "total_budget": 5000,
    "attractions_total": 320,
    "food_total": 600,
    "hotel_total": 840,
    "transport_total": 500,
    "reserve": 2740,  # 预留应急资金 = total_budget - (attractions_total + food_total + hotel_total + transport_total)
    "within_budget": true
  },
  "health_alerts": ["您的行程包含较多步行，建议随身携带日常药物"],
  "preference_compliance": ["已为您排除硬座选项，全程优先选择卧铺/座位"]
}
```

---

## 6. 容错与兜底策略

### 6.1 失败场景与处理

| 失败场景 | 处理策略 |
|---------|---------|
| LLM API 超时 | 重试 1 次（间隔 2s）→ 超时则返回"推荐服务繁忙，请稍后重试" |
| 单个子 Agent 失败 | Supervisor 跳过该 Agent，其他 Agent 继续，返回部分结果并标注 |
| Budget Agent 检测到超支 | 自动触发 Route Agent 调整路线（最多调整 2 次） |
| 所有子 Agent 都失败 | 返回友好兜底话术 + 提供备用引导（"您可以告诉我更具体的偏好"） |
| 模型 API 不可用 | 按序切换备选模型：OpenAI → Claude → 本地模型；触发条件：返回错误码 429（限流，等待 5s 重试）、500（服务端错误，立即切换）、connection timeout（立即切换）；**单次请求粒度**：每个 LLM 调用独立决定用哪个模型，某次调用失败切换后不影响后续调用 |
| SQLite 连接失败 | 降级为纯会话模式（不写长期记忆），返回提示 |

### 6.2 超时配置

| 操作 | 超时时间 |
|------|---------|
| 单次 Tool 调用 | 10s |
| 单个子 Agent 执行 | 30s |
| 完整规划请求 | 90s（超时返回当前进度）|
| LLM API 重试间隔 | 2s |

---

## 7. 监控与性能评测

### 7.1 可观测性

- **结构化日志**：每个请求携带 `trace_id`，记录完整的 Agent 调用链路
- **Prometheus Metrics**：QPS、TP50/TP99 延迟、错误率、子 Agent 耗时分布
- **健康检查**：`/api/health` 定期检查 LLM API 和 SQLite 可用性

### 7.2 性能评测指标

| 指标 | 目标值 |
|------|-------|
| API 响应 TP99 | < 5s（不包含 LLM 调用的场景）|
| 完整规划 TP99 | < 30s（包含 LLM 调用的场景）|
| 错误率 | < 5% |
| 子 Agent 调用成功率 | > 95% |

---

## 8. 项目目录结构

```
smartJournal/
│
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口，路由注册
│   ├── config.py            # 配置（模型、API Key、DB路径）
│   │
│   ├── agents/              # Agent 定义
│   │   ├── __init__.py
│   │   ├── supervisor.py    # Planning Agent（总控）
│   │   ├── attractions.py  # Attractions Agent
│   │   ├── route.py         # Route Agent
│   │   ├── budget.py        # Budget Agent
│   │   ├── food.py          # Food Agent
│   │   ├── hotel.py         # Hotel Agent
│   │   └── preference.py    # Preference Agent
│   │
│   ├── tools/               # Tools 定义
│   │   ├── __init__.py
│   │   ├── attractions_tools.py
│   │   ├── route_tools.py
│   │   ├── budget_tools.py
│   │   ├── food_tools.py
│   │   ├── hotel_tools.py
│   │   └── preference_tools.py
│   │
│   ├── memory/              # 记忆系统
│   │   ├── __init__.py
│   │   ├── short_term.py   # 短期记忆
│   │   └── long_term.py    # 长期记忆（SQLite）
│   │
│   ├── api/                 # API 路由
│   │   ├── __init__.py
│   │   ├── chat.py
│   │   ├── plan.py
│   │   ├── preference.py
│   │   └── monitor.py
│   │
│   ├── services/            # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── planning_service.py
│   │   ├── memory_service.py
│   │   └── metrics_service.py
│   │
│   └── middleware/          # 中间件
│       ├── __init__.py
│       ├── tracing.py       # trace_id 链路追踪
│       └── error_handler.py # 全局异常处理 + 兜底
│
├── tests/                   # 测试
│   ├── agents/
│   ├── tools/
│   └── api/
│
├── data/                    # SQLite 数据库
│   └── memory.db
│
├── docs/                    # 文档
│   └── specs/
│       └── 2026-03-27-travel-multiagent-design.md
│
├── requirements.txt
├── .env.example
└── README.md
```

---

## 9. 设计决策总结

| 决策项 | 选择 | 理由 |
|-------|------|------|
| Agent 协作模式 | Supervisor + Specialist | 清晰好调试，面试展示友好 |
| Preference Agent | 独立模块，其他 Agent 只读 | 偏好集中管理，避免冲突 |
| 长期记忆存储 | SQLite | 轻量免运维，面试可解释 |
| 健康提醒方式 | 主动提醒（非静默过滤）| 体现系统智能度和责任感 |
| 并发模型 | FastAPI + Uvicorn + async | 原生异步，并发能力强 |
| 模型切换 | OpenAI → Claude → 本地 | 多层降级，保证可用性 |

---

*设计文档版本：v1.2 | 最后更新：2026-03-27 | 修复：agent_trace schema 统一、health_alerts 示例对齐规则表、reserve 语义说明、llm_available 双字段语义澄清*
