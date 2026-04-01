# 🧠 Smart Travel Journal

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)
![LangChain](https://img.shields.io/badge/LangChain-0.1+-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**懂你的智能旅行规划个人助理**</br>
打造专属旅行智能体，记住你的偏好、预算与健康需求，量身定制完美行程

</div>

---

## ✨ 核心特色

| 特色 | 说明 |
|------|------|
| 🧑‍💼 **专属个人智能体** | 为每位用户打造专属旅行助手，越用越懂你 |
| 🧠 **终身记忆系统** | 自动记住你的旅行偏好、健康状况、预算习惯，跨会话持久化 |
| ❤️ **健康守护** | 智能识别心脏病、糖尿病等健康风险，主动贴心提醒 |
| 💰 **预算精灵** | 实时监控花费，超支自动优化路线（最多 2 轮调整） |
| 🤖 **Multi-Agent 协作** | 4 个专业 Agent 各司其职，协同生成完整行程 |
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

### 🏛️ 架构图

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

### 🏛️ 4-Agent 各司其职

| Agent | 职责 | 超能力 |
|-------|------|------|
| **PlanningAgent** | 主管协调 | 理解你的意图，统筹整个规划流程 |
| **PreferenceAgent** | 偏好记忆 | 你的专属档案管理员，记住所有偏好 |
| **BudgetAgent** | 预算守护 | 精打细算，超支时自动优化路线 |
| **TravelPlannerAgent** | 行程规划 | 整合搜索与规划，打造专属路线 |

### 📁 项目结构

```
smartJournal/
├── app/
│   ├── agents/              # Agent 定义
│   │   ├── supervisor.py    # PlanningAgent（总控）
│   │   ├── preference.py    # PreferenceAgent（偏好管理）
│   │   ├── budget.py        # BudgetAgent（预算计算）
│   │   └── travel_planner.py # TravelPlannerAgent（整合版）
│   ├── api/                 # FastAPI 路由
│   │   └── chat.py          # 聊天接口
│   ├── graph/               # Prompt 组装
│   │   └── prompt/          # Prompt 组合器
│   ├── memory/               # 记忆文件
│   │   ├── MEMORY.md        # 精选长期记忆
│   │   └── logs/            # 每日会话日志
│   ├── middleware/           # 中间件
│   ├── services/             # 服务层
│   │   ├── memory/          # 记忆系统
│   │   │   ├── short_term.py      # 短期记忆
│   │   │   ├── session_manager.py  # 会话管理
│   │   │   ├── markdown_memory.py  # 长期记忆
│   │   │   ├── memory_injector.py  # 记忆注入
│   │   │   └── daily_log.py        # 每日日志
│   │   ├── model/            # 模型服务
│   │   │   └── model_router.py     # 模型降级链
│   │   └── chat/            # 聊天服务
│   │       └── chat_service.py     # 主聊天入口
│   ├── session/             # 会话管理
│   ├── skills/               # Agent Skills 定义
│   ├── tools/               # 工具定义
│   │   ├── travel_skills.py # 旅行工具（搜索+规划）
│   │   └── budget_tools.py  # 预算工具
│   ├── workspace/           # Agent Prompt 模板
│   │   ├── SOUL.md          # 核心人格和原则
│   │   ├── IDENTITY.md      # Agent 身份模板
│   │   ├── USER.md          # 用户上下文模板
│   │   ├── AGENTS.md        # 多 Agent 协调规则
│   │   ├── TOOLS.md         # 工具配置
│   │   └── BOOTSTRAP.md     # 启动引导
│   ├── config.py            # 配置管理
│   └── main.py              # FastAPI 入口
├── front/                   # React + Vite 前端
├── docs/                    # 设计文档
│   └── superpowers/
│       ├── specs/           # 设计规格
│       └── plans/           # 实现计划
├── tests/                   # 测试
├── .claude/                 # Claude Code 配置
│   └── projects/            # 项目记忆
├── CLAUDE.md                # Claude Code 指导文件
├── guidence.md              # 项目指导文件
└── requirements.txt         # Python 依赖
```

---

## 🔄 如何为你规划行程

1. **📝 理解你的需求** — PlanningAgent 解析目的地、天数、预算和特殊需求
2. **🧠 调用你的画像** — PreferenceAgent 读取你过往的偏好与习惯（如：喜欢深度游、讨厌早起）
3. **⚡ 并行智能规划** — TravelPlannerAgent 搜索景点/餐厅/酒店 + BudgetAgent 计算费用
4. **🗺️ 专属路线生成** — 根据你的节奏和偏好，规划每日行程
5. **💰 预算守护** — 实时校验花费，超支自动调整（最多 2 轮）
6. **❤️ 健康护航** — 结合你的健康档案，生成贴心提醒
7. **📤 交付完整方案** — 整合输出专属于你的旅行计划

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

| 层级 | 技术 | 说明 |
|------|------|------|
| 🌐 Web 框架 | FastAPI + Uvicorn | 高性能异步 API |
| 🤖 Agent 框架 | LangChain | Agent 编排与工具调用 |
| 🧠 主模型 | DeepSeek Chat | 国产强力模型，支持长上下文 |
| 🗃️ 短期记忆 | ConversationBuffer | 会话级上下文保持 |
| 📝 长期记忆 | Markdown 文件 | 用户画像持久化存储 |
| 📊 监控 | Prometheus + structlog | 生产级可观测性 |
| 🎨 前端 | React + Vite + TypeScript | 现代响应式前端 |

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

### 🎨 行程交付升级

- [ ] **可视化行程地图** — 路线图而非文字列表，一目了然
- [ ] **多格式导出** — 一键生成日历邀请、PDF 攻略、分享卡片
- [ ] **社交分享** — 行程分享到社交媒体

### 🔄 数据闭环

- [ ] **旅行后复盘** — 用户点评反馈，反哺下次推荐
- [ ] **个性化榜单** — 基于偏好生成专属 Top 榜单

### 🧠 记忆系统深化

- [ ] **多模态记忆** — 存储景点照片、旅行票据等
- [ ] **知识图谱** — 构建景点关系网络，发现关联玩法

### 🎯 场景化垂直拓展

- [ ] **亲子游模式** — 儿童友好、寓教于乐
- [ ] **银发族模式** — 节奏舒缓、无障碍优先
- [ ] **商务出差模式** — 效率至上、交通便利

### 🌐 实时感知

- [ ] **天气预警** — 景区实时天气与预警提醒
- [ ] **人流预测** — 景区拥挤度实时感知，智能错峰

### 🛠️ Agent 能力扩展

- [ ] **监控面板** — Agent 执行状态、耗时、调用链可视化
- [ ] **更多 Skills** — 引入优质外部工具和 Skills

---

## 📄 License

MIT License - 欢迎 Star ⭐ 和 Fork 🍴

---

<div align="center">

**如果这个项目对你有帮助，请给它一个 ⭐！**

</div>
