# 🧠 Smart Travel Journal

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)
![LangChain](https://img.shields.io/badge/LangChain-0.1+-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**基于 LangChain 的智能出行规划 Multi-Agent 系统**</br>
支持景点推荐、路线规划、预算控制、美食住宿推荐和用户偏好管理

</div>

---

## ✨ 功能特性

| 特性 | 说明 |
|------|------|
| 🤖 **Multi-Agent 协作** | 4 个专业 Agent 协作生成完整行程（Supervisor + 3 Specialists） |
| 🧠 **双层记忆系统** | 短期记忆（会话级）+ 长期记忆（Markdown，跨会话持久化） |
| ❤️ **健康提醒** | 基于用户健康状况主动生成提醒（心脏病、糖尿病等） |
| 💰 **预算控制** | Budget Agent 实时校验，超支自动触发路线调整（最多 2 轮） |
| 🔄 **模型降级链** | DeepSeek → OpenAI → Claude → 本地模型，多层容错保证可用性 |
| 📊 **可观测性** | 结构化日志 + Prometheus Metrics + 链路追踪 |

---

## 🚀 快速开始

### 📦 安装

```bash
# 克隆项目
git clone https://github.com/abelferry-cloud/mind-trip.git
cd mind-trip

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API 密钥
```

### 🏃 启动服务

```bash
# 方式一：直接运行
python -m app.main

# 方式二：使用 uvicorn
uvicorn app.main:app --reload --port 8000
```

> ✅ 服务启动后访问 [http://localhost:8000/docs](http://localhost:8000/docs) 查看 API 文档

---

## 📐 系统架构

### 🏛️ 4-Agent 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    PlanningAgent (主管)                      │
│                   意图解析 · 流程编排 · 结果整合                │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ PreferenceAgent │  │  BudgetAgent    │  │ TravelPlanner   │
│   偏好管理       │  │    预算计算      │  │   整合搜索+规划   │
│  (唯一写入记忆)  │  │   + 验证       │  │ 景点/餐厅/酒店   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### 📁 项目结构

```
smartJournal/
├── app/
│   ├── agents/              # Agent 定义
│   │   ├── supervisor.py   # PlanningAgent（总控）
│   │   ├── preference.py    # PreferenceAgent（偏好管理）
│   │   ├── budget.py        # BudgetAgent（预算计算）
│   │   └── travel_planner.py # TravelPlannerAgent（整合版）
│   ├── api/                 # FastAPI 路由
│   │   ├── chat.py          # 聊天接口
│   │   └── chat_stream.py   # 流式聊天（SSE）
│   ├── services/
│   │   ├── memory/          # 记忆系统
│   │   │   ├── short_term.py    # 短期记忆
│   │   │   ├── session_manager.py # 会话管理
│   │   │   ├── markdown_memory.py # 长期记忆
│   │   │   └── memory_injector.py # 记忆注入
│   │   └── model/           # 模型服务
│   │       └── model_router.py   # 模型降级链
│   ├── tools/               # 工具定义
│   │   ├── travel_skills.py # 旅行工具（搜索+规划）
│   │   └── budget_tools.py  # 预算工具
│   └── graph/               # Prompt 组装
│       └── prompt/          # Prompt 组合器
├── front/                   # React 前端
├── docs/                    # 设计文档
│   └── superpowers/
│       ├── specs/           # 设计规格
│       └── plans/           # 实现计划
└── tests/                   # 测试
```

---

## 🔄 Agent 协作流程

```
用户: "我要去杭州3天，预算5000，我有心脏病"

    ┌──────────────────────────────────────────┐
    │  1️⃣ PlanningAgent 解析意图               │
    │      城市=杭州, 天数=3, 预算=5000         │
    └──────────────────────────────────────────┘
                        │
                        ▼
    ┌──────────────────────────────────────────┐
    │  2️⃣ PreferenceAgent 更新长期记忆          │
    │      健康状况=心脏病                       │
    └──────────────────────────────────────────┘
                        │
          ┌─────────────┴─────────────┐
          ▼                           ▼
    ┌──────────────┐           ┌──────────────┐
    │   并行执行    │           │   并行执行    │
    │ TravelPlanner│           │   Budget     │
    │   Agent      │           │   Agent      │
    │ (搜索景点/    │           │  (计算预算)   │
    │  餐厅/酒店)   │           │              │
    └──────────────┘           └──────────────┘
          │                           │
          └─────────────┬─────────────┘
                        ▼
    ┌──────────────────────────────────────────┐
    │  3️⃣ TravelPlannerAgent 规划每日路线       │
    │      (使用高德地图 API)                    │
    └──────────────────────────────────────────┘
                        │
                        ▼
    ┌──────────────────────────────────────────┐
    │  4️⃣ BudgetAgent 验证总预算                │
    │      ❌ 超支 → 触发重新规划 (最多2轮)      │
    │      ✅ 通过 → 生成健康提醒 + 偏好合规说明   │
    └──────────────────────────────────────────┘
                        │
                        ▼
    ┌──────────────────────────────────────────┐
    │  5️⃣ 返回完整旅行方案                       │
    └──────────────────────────────────────────┘
```

---

## 📡 API 示例

### 💬 聊天接口

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "message": "我要去杭州3天，预算5000，我有心脏病，不喜欢硬座",
    "session_id": "session_001"
  }'
```

### 🌊 流式聊天接口（SSE）

```bash
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "message": "帮我规划一个上海3日游",
    "session_id": "session_001"
  }'
```

### 📋 响应示例

```json
{
  "answer": "为您规划了杭州3天行程，祝您旅途愉快！",
  "plan_id": "plan_abc123",
  "agent_trace": {
    "agents": ["PlanningAgent", "PreferenceAgent", "BudgetAgent", "TravelPlannerAgent"],
    "durations_ms": [12, 45, 230, 1850],
    "errors": []
  },
  "health_alerts": ["您的行程包含较多步行，建议随身携带日常药物并避免剧烈活动"]
}
```

---

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| 🌐 Web 框架 | FastAPI + Uvicorn |
| 🤖 Agent 框架 | LangChain |
| 🧠 主模型 | DeepSeek Chat |
| 🗃️ 短期记忆 | LangChain ConversationBuffer |
| 📝 长期记忆 | Markdown 文件 (app/memory/) |
| 📊 监控 | Prometheus + structlog |
| 🎨 前端 | React + Vite + TypeScript |

---

## 🔧 配置说明

主要配置项在 `.env` 文件中：

```env
# 主要 LLM (DeepSeek)
deepseek_api_key=your_api_key_here
deepseek_base_url=https://api.deepseek.com
deepseek_model=deepseek-chat

# 备用 LLM
openai_api_key=
openai_model=gpt-4o-mini
claude_api_key=

# 模型故障转移顺序
model_chain=deepseek,openai,claude,local

# 外部 API
tavily_api_key=
amap_api_key=
```

---

## 📈 RoadMap

- [ ] 连接真实旅行 API（高德地图、携程等）
- [ ] 添加多语言支持
- [ ] 支持团队出行规划
- [ ] 添加行程分享功能
- [ ] WebSocket 实时通信

---

## 📄 License

MIT License - 欢迎 Star ⭐ 和 Fork 🍴

---

<div align="center">

**如果这个项目对你有帮助，请给它一个 ⭐！**

</div>
