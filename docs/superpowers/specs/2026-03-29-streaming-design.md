# 流式输出 (Streaming) 功能设计

**日期：** 2026-03-29
**状态：** 待实施
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
│  /api/chat/ │                   │  EventSource     │
│   stream    │                   │  └─ 状态面板      │
└─────────────┘                   └──────────────────┘
```

---

## 3. 后端设计

### 3.1 新端点

**端点：** `GET /api/chat/stream`（通过 query params: `?session_id=xxx&user_id=xxx`）

**响应：** `text/event-stream` (SSE)

**CORS 配置：** 复用现有 CORS 中间件配置，无需额外修改。

**重连机制：** SSE 响应包含 `retry: 5000` 字段，告诉浏览器断连后等待 5 秒再重连。

**心跳机制：** 每 15 秒发送 `ping` 事件保持连接活跃。

### 3.2 SSE 事件类型

| 事件名 | 触发时机 | 数据内容 |
|--------|----------|----------|
| `agent_switch` | Agent 切换时 | `{agent: "PlanningAgent"}` |
| `model_switch` | 模型切换时（fallback） | `{model: "claude", reason: "rate_limit"}` |
| `iteration` | 工具调用循环次数 | `{iteration: 1, max_iterations: 10}` |
| `tool_start` | 工具开始调用 | `{tool: "search_attractions", tool_call_id: "call_xxx"}` |
| `tool_end` | 工具调用完成 | `{tool: "search_attractions", result: {...}, duration_ms: 120}` |
| `tool_error` | 工具执行失败 | `{tool: "search_attractions", error: "timeout"}` |
| `token_usage` | token 统计 | `{prompt_tokens: 100, completion_tokens: 50, total_tokens: 150}` |
| `reasoning_step` | 推理步骤 | `{step: "分析用户偏好：深度体验型"}` |
| `content_chunk` | 内容片段 | `{content: "正在为你规划..."}` |
| `final` | 完成 | `{answer: "完整回复"}` |
| `error` | 错误 | `{error: "错误信息"}` |
| `ping` | 心跳（保持连接） | `{}` |

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
    async def model_switch(self, model: str, reason: str): ...
    async def iteration(self, iteration: int, max_iterations: int): ...
    async def tool_start(self, tool: str, tool_call_id: str): ...
    async def tool_end(self, tool: str, result: Any, duration_ms: int): ...
    async def tool_error(self, tool: str, error: str): ...
    async def token_usage(self, prompt_tokens: int, completion_tokens: int, total_tokens: int): ...
    async def reasoning_step(self, step: str): ...
    async def content_chunk(self, content: str): ...
    async def final(self, answer: str): ...
    async def error(self, error: str): ...
    async def ping(self): ...  # 心跳
```

### 3.5 认证（安全考虑）

SSE 端点通过 `user_id` + `session_id` 标识会话。初期实现复用现有的简单认证模式。后续应引入真实的用户认证机制（JWT / Session）防止会话劫持。

---

## 4. 前端设计

### 4.1 状态结构

**设计原则：** 与 Stage.jsx 的 `session.messages` 模式对齐，不引入独立的 `streamingState`。流式状态作为消息对象的扩展字段。

```jsx
// 消息对象扩展
const streamingMessage = {
  id: 'temp_123',
  role: 'assistant',
  content: '',  // 打字机效果逐步填充
  streaming: true,  // 标记为流式消息
  status: 'streaming', // 'streaming' | 'done' | 'error'
  agent: 'PlanningAgent',
  toolCalls: [], // [{tool, status: 'running'|'done'|'error', duration_ms?, result?}]
  tokenUsage: null,
  reasoningSteps: [],
}
```

**状态面板独立于消息存在：**
- 状态面板的数据来源是当前活跃消息的扩展字段（`agent`, `toolCalls`, `tokenUsage`, `reasoningSteps`）
- `contentBuffer` 和打字机效果直接作用于消息的 `content` 字段
- 流式完成后，`streaming: false`，消息变为普通消息

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

- 使用 `setInterval` + `performance.now()` 计时，不依赖 `requestAnimationFrame`（浏览器后台会暂停）
- 每收到 `content_chunk` 事件，累积到 `contentBuffer`
- 打字速度：约 20ms/字符（可配置）
- 收到 `final` 事件后，直接显示完整内容，停止打字机

### 4.4 EventSource 管理

```jsx
// 在 Stage.jsx 中
const eventSourceRef = useRef(null)

const startStreaming = (sessionId, message) => {
  // 1. 创建流式消息（占位）
  const tempMessage = { ...message, streaming: true, status: 'streaming' }
  appendMessage(tempMessage)

  // 2. 连接 SSE
  const es = new EventSource(`/api/chat/stream?session_id=${sessionId}&user_id=${userId}`)
  eventSourceRef.current = es

  // 3. 注册所有事件处理器
  es.addEventListener('agent_switch', (e) => {
    updateMessage(tempMessage.id, { agent: JSON.parse(e.data).agent })
  })

  es.addEventListener('model_switch', (e) => {
    updateMessage(tempMessage.id, { model: JSON.parse(e.data).model })
  })

  es.addEventListener('iteration', (e) => {
    const {iteration, max_iterations} = JSON.parse(e.data)
    updateMessage(tempMessage.id, { iteration, max_iterations })
  })

  es.addEventListener('tool_start', (e) => {
    const {tool, tool_call_id} = JSON.parse(e.data)
    appendToolCall(tempMessage.id, {tool, status: 'running', tool_call_id})
  })

  es.addEventListener('tool_end', (e) => {
    const {tool, result, duration_ms} = JSON.parse(e.data)
    updateToolCall(tempMessage.id, tool, {status: 'done', result, duration_ms})
  })

  es.addEventListener('tool_error', (e) => {
    const {tool, error} = JSON.parse(e.data)
    updateToolCall(tempMessage.id, tool, {status: 'error', error})
  })

  es.addEventListener('token_usage', (e) => {
    updateMessage(tempMessage.id, { tokenUsage: JSON.parse(e.data) })
  })

  es.addEventListener('reasoning_step', (e) => {
    appendReasoningStep(tempMessage.id, JSON.parse(e.data).step)
  })

  es.addEventListener('content_chunk', (e) => {
    const {content} = JSON.parse(e.data)
    typewriterAppend(tempMessage.id, content)
  })

  es.addEventListener('final', (e) => {
    const {answer} = JSON.parse(e.data)
    finalizeMessage(tempMessage.id, answer)
    es.close()
  })

  es.addEventListener('error', (e) => {
    handleStreamError(tempMessage.id, JSON.parse(e.data).error)
    es.close()
  })

  es.addEventListener('ping', () => {})  // 心跳，无需处理
}
```

**辅助函数（需在 Stage.jsx 中实现）：**
- `appendMessage(msg)` — 添加消息到 session.messages
- `updateMessage(id, patch)` — 根据 id 更新消息字段
- `appendToolCall(msgId, toolCall)` — 追加工具调用到消息的 toolCalls 数组
- `updateToolCall(msgId, toolName, patch)` — 更新指定工具调用的状态
- `appendReasoningStep(msgId, step)` — 追加推理步骤
- `typewriterAppend(msgId, chunk)` — 打字机效果：累积 content
- `finalizeMessage(id, answer)` — 流式完成：设置完整 answer，streaming=false
- `handleStreamError(id, error)` — 处理错误状态
```

### 4.5 改造文件

1. **改造 `frontend/src/components/Stage.jsx`** — 添加 EventSource 连接、状态面板渲染、打字机效果逻辑
2. **改造 `frontend/src/App.jsx`** — 无需大改，Props 接口保持兼容

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
| 工具执行失败 | 发出 `tool_error` 事件，面板显示该工具错误状态 |
| LLM 调用失败 | 发出 `error` 事件，优雅降级显示错误信息 |
| 达到最大迭代次数 | 发出 `error` 事件（reason: "max_iterations"） |

---

## 7. 向后兼容

- 保留现有 `POST /api/chat` 非流式端点
- 新增 `POST /api/chat/stream` SSE 端点
- 前端通过 UI 开关或配置选择使用哪个端点
