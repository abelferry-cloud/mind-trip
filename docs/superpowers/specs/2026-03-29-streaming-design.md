# 流式输出 (Streaming) 功能设计

**日期：** 2026-03-29
**状态：** 已批准
**技术方案：** Server-Sent Events (SSE)

---

## 1. 概述

实现前端实时展示大模型推理状态的功能，包括：
- 工具调用链（开始/结束、耗时、结果）
- Token 消耗统计
- Agent 切换
- 推理步骤
- 内容打字机效果

---

## 2. 架构

```
┌─────────────┐    SSE Events     ┌──────────────────┐
│  FastAPI    │ ───────────────▶  │  React Frontend  │
│  /api/chat  │                   │  EventSource     │
│  (streaming)│                   │  └─ 状态面板      │
└─────────────┘                   └──────────────────┘
```

---

## 3. 后端设计

### 3.1 新端点

**端点：** `POST /api/chat/stream`

**响应：** `text/event-stream` (SSE)

### 3.2 SSE 事件类型

| 事件名 | 触发时机 | 数据内容 |
|--------|----------|----------|
| `agent_switch` | Agent 切换时 | `{agent: "PlanningAgent"}` |
| `tool_start` | 工具开始调用 | `{tool: "search_attractions", tool_call_id: "call_xxx"}` |
| `tool_end` | 工具调用完成 | `{tool: "search_attractions", result: {...}, duration_ms: 120}` |
| `token_usage` | token 统计 | `{prompt_tokens: 100, completion_tokens: 50, total_tokens: 150}` |
| `reasoning_step` | 推理步骤 | `{step: "分析用户偏好：深度体验型"}` |
| `content_chunk` | 内容片段 | `{content: "正在为你规划..."}` |
| `final` | 完成 | `{answer: "完整回复"}` |
| `error` | 错误 | `{error: "错误信息"}` |

### 3.3 改造文件

1. **新增 `app/api/chat_stream.py`** — SSE 流式端点
2. **改造 `app/services/tool_calling_service.py`** — 在工具调用前后发射 SSE 事件
3. **改造 `app/services/model_router.py`** — 捕获 token usage 并发射事件
4. **新增 `app/services/stream_manager.py`** — SSE 事件发射器（单例模式，供各服务调用）

### 3.4 事件发射接口

```python
class StreamManager:
    async def emit(self, event_name: str, data: dict): ...

    async def agent_switch(self, agent: str): ...
    async def tool_start(self, tool: str, tool_call_id: str): ...
    async def tool_end(self, tool: str, result: Any, duration_ms: int): ...
    async def token_usage(self, prompt_tokens: int, completion_tokens: int, total_tokens: int): ...
    async def reasoning_step(self, step: str): ...
    async def content_chunk(self, content: str): ...
    async def final(self, answer: str): ...
    async def error(self, error: str): ...
```

---

## 4. 前端设计

### 4.1 状态结构

```jsx
const [streamingState, setStreamingState] = useState({
  status: 'idle', // 'idle' | 'streaming' | 'done' | 'error'
  agent: null,
  toolCalls: [], // [{tool, status: 'running'|'done'|'error', duration_ms?, result?}]
  tokenUsage: null, // {prompt_tokens, completion_tokens, total_tokens}
  reasoningSteps: [],
  contentBuffer: '',
  fullAnswer: '',
})
```

### 4.2 状态面板 UI

**位置：** AI 消息气泡下方，类似现有的 thoughts 展开

**面板结构：**
```
┌─ 推理过程 ─────────────────────────┐
│ 🤖 PlanningAgent                   │
│   🔧 search_attractions (进行中...) │
│   ✅ 搜索完成，找到 12 个景点 (120ms)│
│   📊 Token: 150 / 50 / 200         │
│   💭 分析用户偏好：深度体验型       │
├─────────────────────────────────────┤
│ 📝 最终回复正在打字机效果显示...     │
└─────────────────────────────────────┘
```

### 4.3 打字机效果

- 使用 `setInterval` 或 `requestAnimationFrame` 逐字显示
- 每收到 `content_chunk` 事件，累积到 `contentBuffer`
- 打字速度：约 20ms/字符（可配置）

### 4.4 改造文件

1. **改造 `frontend/src/components/Stage.jsx`** — 添加 EventSource 连接和状态面板
2. **改造 `frontend/src/App.jsx`** — 传递 SSE 相关 props（可选：统一状态管理）

---

## 5. 数据流

```
用户发送消息
    │
    ▼
EventSource 连接 /api/chat/stream
    │
    ▼
ToolCallingService.call_with_tools()
    │ 工具开始
    ▼ emit SSE: tool_start
    │
    │ 执行工具 (120ms)
    │
    ▼ emit SSE: tool_end, token_usage
    │
    │ 继续 LLM 循环...
    │
    ▼ emit SSE: content_chunk (每个片段)
    │
    ▼ emit SSE: final, {answer: "..."}
```

---

## 6. 错误处理

| 场景 | 处理方式 |
|------|----------|
| SSE 连接断开 | 前端显示"连接中断"，显示重连按钮 |
| 工具执行失败 | 发出 `error` 事件，面板显示错误状态 |
| LLM 调用失败 | 发出 `error` 事件，优雅降级显示错误信息 |

---

## 7. 向后兼容

- 保留现有 `POST /api/chat` 非流式端点
- 新增 `POST /api/chat/stream` SSE 端点
- 前端通过 UI 开关或配置选择使用哪个端点
