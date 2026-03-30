# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Smart Travel Journal** is a Multi-Agent Trip Planning System using FastAPI + LangChain. It coordinates 4 specialized agents (Supervisor + 3 Specialists) to generate complete travel itineraries with budget control, health alerts, and preference memory.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python -m app.main
# or with uvicorn
uvicorn app.main:app --reload --port 8000

# Run tests (if any exist)
pytest tests/ -v

# Access API docs: http://localhost:8000/docs
```

## Tool Usage Guidelines

When working with LangChain or LangGraph, always use the official MCP tools and skills to ensure correct usage:

1. **LangChain**: Use the `mcp__plugin_context7_context7__*` MCP tools to query LangChain official documentation
2. **LangGraph**: Use the `langchain-skills:langgraph-fundamentals` skill to query LangGraph official documentation
3. **Web Search**: Use the `mcp__MiniMax__web_search` MCP tool for internet searches

## OpenClaw Architecture Reference

This project references **OpenClaw**'s architecture design, including:

- Context management
- Prompt design
- Memory implementation
- Agent coordination patterns
- etc...

OpenClaw emphasizes **lightweight** and **high transparency**. If you are unfamiliar with OpenClaw's architecture or unclear about prompt design decisions, use the `mcp__MiniMax__web_search` MCP tool to search for accurate information. **Do not speculate** — always verify with official sources.

## Architecture

### Multi-Agent System (4-Agent Architecture)

项目采用精简的4-Agent架构（已从原来的7-Agent重构）：

```
PlanningAgent (Supervisor/主管)
├── PreferenceAgent (偏好管理)
├── BudgetAgent (预算计算与验证)
└── TravelPlannerAgent (旅行规划 - 整合版)
```

**Agent 职责说明：**

| Agent | 职责 | 特点 |
|-------|------|------|
| **PlanningAgent** | 主管协调，解析意图，编排执行流程 | 唯一入口，管理整个规划生命周期 |
| **PreferenceAgent** | 解析并更新用户偏好到长期记忆 | 唯一可写入 Markdown 记忆的 Agent |
| **BudgetAgent** | 预算计算、验证、超预算检测 | 支持重新规划触发 |
| **TravelPlannerAgent** | 整合搜索+规划：景点、餐厅、酒店、路线 | 替代原有多个专项 Agent |

**Agent Coordination Flow:**
1. PlanningAgent 解析用户意图（城市、天数、预算、偏好）
2. PreferenceAgent 更新长期记忆（唯一写入 MEMORY.md 的 Agent）
3. 并行执行：TravelPlannerAgent（搜索景点/餐厅/酒店）+ BudgetAgent（计算预算）
4. TravelPlannerAgent 规划每日路线（使用高德地图 API）
5. BudgetAgent 验证总预算
6. 如果超预算 → 触发 TravelPlannerAgent 重新规划（最多 2 次重试）
7. 生成健康提醒 + 偏好合规说明
8. 返回完整旅行方案

### Memory Architecture

**静态记忆文件**存储在 `app/memory/`：
- `MEMORY.md` - 精选的长期记忆 Markdown
- `logs/YYYY-MM-DD.md` - 每日会话日志

**所有记忆逻辑代码**集中在 `app/services/memory/`：

| Layer | Storage | Access |
|-------|---------|--------|
| Short-term | `app/services/memory/short_term.py` - ShortTermMemory | 基于 LangChain 的 ConversationBufferMemory |
| Session | `app/services/memory/session_manager.py` - SessionMemoryManager | 会话级记忆管理 |
| Long-term | `app/services/memory/markdown_memory.py` - MarkdownMemoryManager | PreferenceAgent 写，其他只读 |
| Daily logs | `app/services/memory/daily_log.py` - DailyLogManager | 按天追加日志 |
| Memory Injection | `app/services/memory/memory_injector.py` - MemoryInjector | 会话启动时注入记忆到 System Prompt |

### Model Fallback Chain

`deepseek → openai → claude → local`（通过 `model_chain` 在 `.env` 配置）

主要模型是 DeepSeek（通过 `deepseek_api_key` 配置）。

### Workspace Files

Agent prompts 从 `app/workspace/` Markdown 文件动态组装：
- `SOUL.md` - 核心人格和原则
- `IDENTITY.md` - Agent 身份模板
- `USER.md` - 用户上下文模板
- `AGENTS.md` - 多 Agent 协调规则
- `TOOLS.md` - 工具配置
- `BOOTSTRAP.md` - 启动引导
- `SYSTEM_PROMPT_*.md` - Agent 专属 System Prompt

Prompt 组装逻辑在 `app/graph/prompt/` 模块：
- `composer.py` - PromptComposer 主组装器
- `workspace_loader.py` - 加载 workspace/*.md
- `memory_loader.py` - 加载记忆内容
- `system_builder.py` - System Prompt 构建器

### Key Files

| Path | Purpose |
|------|---------|
| `app/main.py` | FastAPI 入口，生命周期管理，中间件，路由 |
| `app/config.py` | Pydantic Settings 配置（读取 `.env`） |
| `app/agents/supervisor.py` | PlanningAgent - 主管协调器 |
| `app/agents/preference.py` | PreferenceAgent - 偏好管理（写 MEMORY.md） |
| `app/agents/budget.py` | BudgetAgent - 预算计算与验证 |
| `app/agents/travel_planner.py` | TravelPlannerAgent - 整合搜索+规划 |
| `app/services/chat/chat_service.py` | 主聊天入口 - 编排 prompt、记忆、模型路由 |
| `app/services/model/model_router.py` | LLM 故障转移链 + 重试逻辑 |
| `app/services/memory/session_manager.py` | 会话级 ConversationBufferMemory 管理 |
| `app/services/memory/markdown_memory.py` | 长期 MEMORY.md 管理器 |
| `app/services/memory/memory_injector.py` | 会话启动时将记忆注入 System Prompt |
| `app/graph/sys_prompt_builder.py` | 向后兼容层，代理到 app/graph/prompt/ |
| `app/tools/travel_skills.py` | LangChain Tools：景点/餐厅/酒店搜索、路线规划 |
| `app/tools/budget_tools.py` | 预算计算和验证工具 |

### Observability

- **Tracing**: `trace_id` 中间件为所有日志添加关联 ID
- **Metrics**: Prometheus 客户端在 `/api/metrics/prometheus`
- **Structured Logging**: structlog + JSON 输出

## Configuration

所有配置通过 `app/config.py` → pydantic-settings → `.env`：

```env
# 主要 LLM (DeepSeek)
deepseek_api_key=
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

# 数据库
database_url=data/memory.db

# 记忆目录
memory_dir=app/memory
memory_file=app/memory/MEMORY.md
```

## Note

- `app/tools/` 中的实现使用 **模拟数据**（硬编码景点、餐厅、酒店）。这是演示多 Agent 协调的原型架构，未连接真实旅行 API。
- TravelPlannerAgent 是**整合版 Agent**，替代了原有的 AttractionsAgent、FoodAgent、HotelAgent、RouteAgent 等多个专项 Agent。
- Prompt 系统采用**分层架构**：System Prompt → Workspace Context → Memory Context → User Message。

## Frontend

`frontend/` 目录包含 React + Vite 应用：

```bash
cd frontend && npm install
npm run dev    # 启动开发服务器
npm run build  # 生产构建
```

通过 `/api/chat` 或 `/api/chat/stream` 端点与 FastAPI 后端通信。

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | 非流式聊天 |
| `/api/chat/stream` | POST | 流式聊天（SSE） |
| `/api/plan` | POST | 旅行规划 |
| `/api/preference` | GET/POST | 偏好管理 |
| `/api/session` | GET/POST/DELETE | 会话管理 |
| `/api/workspace/files` | GET | 获取 workspace 文件列表 |
| `/api/metrics/prometheus` | GET | Prometheus 指标 |
| `/api/health` | GET | 健康检查 |
