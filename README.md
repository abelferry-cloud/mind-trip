# Smart Travel Journal - Multi-Agent Trip Planner

基于 LangChain 的智能出行规划 Multi-Agent 系统，支持景点推荐、路线规划、预算控制、美食住宿推荐和用户偏好管理。

## 功能特性

- **Multi-Agent 协作**：Supervisor + Specialist 模式，7 个专业 Agent 协作生成完整行程
- **双层记忆系统**：短期记忆（会话级）+ 长期记忆（SQLite，跨会话持久化）
- **健康提醒**：基于用户健康状况主动生成提醒（心脏病、糖尿病等）
- **预算控制**：Budget Agent 实时校验，超支自动触发路线调整（最多 2 轮）
- **模型降级**：OpenAI → Claude → 本地模型，多层容错保证可用性
- **可观测性**：结构化日志 + Prometheus Metrics + 链路追踪

## 快速开始

### 安装

```bash
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 OPENAI_API_KEY 等配置
```

### 启动服务

```bash
python -m app.main
# 或
uvicorn app.main:app --reload --port 8000
```

服务启动后访问：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/health
- Metrics：http://localhost:8000/api/metrics

### 运行测试

```bash
pytest tests/ -v
```

## API 示例

**规划行程：**

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "message": "我要去杭州3天，预算5000，我有心脏病，不喜欢硬座",
    "session_id": "session_001"
  }'
```

**响应示例：**

```json
{
  "answer": "为您规划了杭州3天行程，祝您旅途愉快！",
  "plan_id": "plan_abc123",
  "agent_trace": {
    "agents": ["Planning Agent", "Attractions Agent", "Budget Agent", "Route Agent", "Food Agent", "Hotel Agent", "Budget Agent (validation)"],
    "durations_ms": [12, 890, 450, 1200, 320, 280, 180],
    "errors": []
  },
  "health_alerts": ["您的行程包含较多步行，建议随身携带日常药物并避免剧烈活动"]
}
```

## 项目架构

```
app/
├── agents/          # Agent 定义
│   ├── supervisor.py  # Planning Agent（总控）
│   ├── attractions.py  # Attractions Agent
│   ├── route.py        # Route Agent
│   ├── budget.py       # Budget Agent
│   ├── food.py         # Food Agent
│   ├── hotel.py        # Hotel Agent
│   └── preference.py   # Preference Agent
├── tools/            # Tools 定义
├── memory/           # 记忆系统
│   ├── short_term.py  # 短期记忆
│   └── long_term.py   # 长期记忆（SQLite）
├── api/              # FastAPI 路由
├── services/         # 业务逻辑服务
└── middleware/       # 中间件

docs/superpowers/specs/   # 设计文档
docs/superpowers/plans/   # 实现计划
```

## Agent 协作流程

1. Planning Agent 解析用户意图（目的地、天数、预算、偏好）
2. Preference Agent 更新长期记忆（心脏病、硬座禁忌等）
3. 并行调用：Attractions Agent + Budget Agent
4. Route Agent 生成每日路线
5. 并行调用：Food Agent + Hotel Agent
6. Budget Agent 校验是否超支 → 必要时触发 Route Agent 调整（最多 2 轮）
7. 生成健康提醒 + 偏好合规说明
8. 整合输出完整行程方案

## 技术栈

| 层级 | 技术 |
|------|------|
| Web 框架 | FastAPI + Uvicorn |
| Agent 框架 | LangChain |
| 模型 | OpenAI GPT-4o-mini |
| 短期记忆 | LangChain ConversationBuffer |
| 长期记忆 | SQLite (aiosqlite) |
| 监控 | Prometheus + structlog |

## License

MIT
