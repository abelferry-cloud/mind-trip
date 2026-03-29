# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Smart Travel Journal** is a Multi-Agent Trip Planning System using FastAPI + LangChain. It coordinates 7 specialized agents (Supervisor + Specialists) to generate complete travel itineraries with budget control, health alerts, and preference memory.

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

### Multi-Agent System (Star Topology)

```
PlanningAgent (Supervisor)
├── AttractionsAgent
├── RouteAgent
├── BudgetAgent
├── FoodAgent
├── HotelAgent
└── PreferenceAgent
```

**Agent Coordination Flow:**
1. PlanningAgent parses user intent (city, days, budget, preferences)
2. PreferenceAgent updates long-term memory (only agent that writes to SQLite)
3. Parallel: AttractionsAgent + BudgetAgent
4. RouteAgent generates daily itinerary
5. Parallel: FoodAgent + HotelAgent
6. BudgetAgent validates → triggers RouteAgent replan if over budget (max 2 retries)
7. Generate health alerts + preference compliance notes
8. Return complete plan

### Memory Architecture

**All memory files are stored under `app/memory/`** — never use `app/workspace/memory/`.

| Layer | Storage | Access |
|-------|---------|--------|
| Short-term | In-memory (`session_manager.py`) - LangChain ConversationBufferMemory | All agents read/write via ChatService |
| Long-term | `app/memory/MEMORY.md` - curated markdown | PreferenceAgent write-only, others read-only |
| Daily logs | `app/memory/YYYY-MM-DD.md` - daily session logs | Session-level append per day |

### Model Fallback Chain

`openai → claude → local` (configured via `model_chain` in `.env`)

Primary model is DeepSeek (configured via `deepseek_api_key`).

### Workspace Files

Agent prompts are dynamically assembled from `app/workspace/` markdown files:
- `SOUL.md` - Core personality and principles
- `IDENTITY.md` - Agent identity template
- `USER.md` - User context template
- `AGENTS.md` - Multi-agent coordination rules
- `TOOLS.md` - Tool configuration
- `SYSTEM_PROMPT_*.md` - Agent-specific system prompts

### Key Files

| Path | Purpose |
|------|---------|
| `app/main.py` | FastAPI entry point with lifespan, middleware, routes |
| `app/config.py` | pydantic-settings configuration (reads `.env`) |
| `app/services/chat_service.py` | Main chat entry point - orchestrates prompt loading, memory, and model routing |
| `app/services/model_router.py` | LLM fallback chain with retry logic |
| `app/agents/supervisor.py` | PlanningAgent - main coordinator (star topology supervisor) |
| `app/agents/preference.py` | Writes to long-term SQLite memory |
| `app/memory/long_term.py` | SQLite schema: preferences, trip_history, feedback |
| `app/memory/session_manager.py` | SessionMemoryManager - per-session ConversationBufferMemory |
| `app/memory/daily_log.py` | DailyLogManager - appends session logs to `app/memory/YYYY-MM-DD.md` |
| `app/memory/markdown_memory.py` | Long-term MEMORY.md manager |
| `app/graph/sys_prompt_builder.py` | Assembles agent prompts from workspace/*.md |

### Observability

- **Tracing**: `trace_id` middleware adds correlation ID to all logs
- **Metrics**: Prometheus client at `/api/metrics/prometheus`
- **Structured Logging**: structlog with JSON output

## Configuration

All settings via `app/config.py` → pydantic-settings → `.env`:

```env
# Primary LLM (DeepSeek)
deepseek_api_key=
deepseek_base_url=https://api.deepseek.com
deepseek_model=deepseek-chat

# Fallback LLMs
openai_api_key=
openai_model=gpt-4o-mini
claude_api_key=

# Model fallback order
model_chain=openai,claude,local

# Database
database_url=data/memory.db
```

## Note

The `app/tools/` implementations use **mock data** (hardcoded attractions, restaurants, hotels). This is a prototype architecture demonstrating multi-agent coordination, not connected to real travel APIs.

## Frontend

The `frontend/` directory contains a React + Vite application:

```bash
cd frontend && npm install
npm run dev    # Start development server
npm run build  # Production build
```

It communicates with the FastAPI backend at `http://localhost:8000` via the `/api/chat` endpoint.
