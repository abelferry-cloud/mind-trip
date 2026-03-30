# 流式输出 (Streaming) 功能设计

**日期：** 2026-03-29
**状态：** 已批准（修订版 v2）
**技术方案：** LangChain 风格 Callback + SSE

---

## 1. 概述

实现前端实时展示大模型推理状态的功能，包括：
- 工具调用链（开始/结束、耗时、结果摘要）
- Token 消耗统计（prompt/completion/total + 成本估算）
- Agent 切换
- LLM 推理步骤（逐 token 输出 + 打字机效果）
- 优雅降级与错误恢复

**设计原则：** 采用 LangChain 风格 `BaseCallbackHandler` 标准化接口 + 自研 SSE 传输层，既利用 LangChain 成熟生态，又保持 FastAPI + 自研 Agent 架构的灵活性。

---

## 2. 架构

```
┌─────────────────────────────────────────────────────────────┐
│                      LangChain 风格                          │
│  StreamCallbackHandler (BaseCallbackHandler 实现)           │
│  - on_llm_start / on_llm_new_token / on_llm_end           │
│  - on_tool_start / on_tool_end                            │
│  - Token usage tracking                                    │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   StreamManager (SSE)                       │
│  - 统一事件发射 (agent_switch, tool_start/end, etc.)       │
│  - session_id 级别的队列管理                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI SSE Endpoint                        │
│  POST /api/chat/stream                                     │
│  - EventSource 保持连接                                    │
│  - 心跳 ping (15s)                                         │
│  - 重试机制 (5s)                                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 React Frontend                              │
│  - EventSource 接收事件                                    │
│  - 内联展开式状态面板                                       │
│  - 打字机效果 (20ms/字符)                                  │
│  - 优雅降级 + 重新发送                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 后端设计

### 3.1 新增端点

**端点：** `POST /api/chat/stream`

**请求体：**
```json
{
  "user_id": "string",
  "session_id": "string",
  "message": "string"
}
```

**响应：** `text/event-stream` (SSE)

**CORS 配置：** SSE 端点需配置 CORS 头部，允许前端开发服务器 (`localhost:5173` Vite / `localhost:3000` CRA) 访问。

**重连机制：** SSE 响应包含 `retry: 5000` 字段，告诉浏览器断连后等待 5 秒再重连。

**心跳机制：** 每 15 秒发送 `ping` 事件保持连接活跃。

### 3.2 SSE 事件类型

| 事件名 | 触发时机 | 数据内容 |
|--------|----------|----------|
| `agent_switch` | Agent 切换时 | `{agent: "PlanningAgent"}` |
| `model_switch` | 模型切换时（fallback） | `{model: "claude", reason: "rate_limit"}` |
| `iteration` | 工具调用循环次数 | `{iteration: 1, max_iterations: 10}` |
| `llm_start` | LLM 开始推理 | `{model: "deepseek-chat"}` |
| `llm_new_token` | 每个新 token（打字机） | `{token: "你", ...}` |
| `llm_end` | LLM 生成完成 | `{total_tokens: 200, ...}` |
| `tool_start` | 工具开始调用 | `{tool: "search_attractions", tool_call_id: "call_xxx"}` |
| `tool_end` | 工具调用完成 | `{tool: "search_attractions", summary: "找到 12 个景点", duration_ms: 120}` |
| `tool_error` | 工具执行失败 | `{tool: "search_attractions", error: "timeout"}` |
| `token_usage` | Token 统计 | `{prompt_tokens: 100, completion_tokens: 50, total_tokens: 150, cost_usd: 0.002}` |
| `reasoning_step` | 推理步骤（LLM 思考过程） | `{step: "分析用户偏好：深度体验型"}` |
| `iteration` | 工具调用循环次数变化 | `{iteration: 1, max_iterations: 10}` |
| `final` | 完成 | `{answer: "完整回复"}` |
| `error` | 错误 | `{error: "错误信息", recoverable: true}` |
| `ping` | 心跳 | `{}` |

### 3.3 新增/改造文件

| 文件 | 描述 |
|------|------|
| `app/api/chat_stream.py` | 新增 SSE 流式端点 |
| `app/services/stream_callback.py` | 新增 LangChain 风格 CallbackHandler |
| `app/services/stream_manager.py` | 增强：添加 `llm_start/new_token/end` 事件 |
| `app/services/tool_calling_service.py` | 集成 StreamCallback，发射工具调用事件 |
| `app/services/model_router.py` | 捕获 token usage，发射 `token_usage` 事件 |

### 3.4 StreamCallbackHandler 接口

```python
class StreamCallbackHandler(BaseCallbackHandler):
    """LangChain 风格回调处理器。

    实现以下方法：
    - on_llm_start: 发射 llm_start 事件
    - on_llm_new_token: 发射 llm_new_token 事件（用于打字机效果）
    - on_llm_end: 发射 llm_end + token_usage 事件
    - on_tool_start: 发射 tool_start 事件
    - on_tool_end: 发射 tool_end 事件（结果截取为摘要）
    - on_reasoning_step: 发射 reasoning_step 事件（LLM 思考过程）
    - on_iteration: 发射 iteration 事件（工具调用循环次数）
    """

    def __init__(self, stream_manager: StreamManager, session_id: str):
        self._stream_manager = stream_manager
        self._session_id = session_id
        self._iteration = 0

    async def on_tool_end(
        self,
        name: str,
        tool_result: Any,
        duration_ms: int,
    ) -> None:
        """工具结束时的回调。

        将完整结果截取为摘要，避免 SSE 传输过大数据。
        """
        summary = self._summarize_result(tool_result)
        await self._stream_manager.tool_end(self._session_id, name, summary, duration_ms)

    async def on_reasoning_step(self, step: str) -> None:
        """发射 LLM 推理步骤。

        当 LLM 输出思考过程（如 <think>...</think> 标签内容）时触发。
        """
        await self._stream_manager.reasoning_step(self._session_id, step)

    async def on_iteration(self, iteration: int, max_iterations: int) -> None:
        """发射工具调用循环次数。

        iteration 从 1 开始计数，max_iterations 来自配置（默认 10）。
        """
        self._iteration = iteration
        await self._stream_manager.iteration(self._session_id, iteration, max_iterations)
```

### 3.5 Token 统计

```python
@dataclass
class TokenStats:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float

# DeepSeek 单价参考（实际以配置为准）
DEEPSEEK_PRICE_PER_1K_TOKENS = 0.001  # 近似值
```

### 3.6 认证

SSE 端点通过 `user_id` + `session_id` 标识会话。复用现有简单认证模式。

---

## 4. 前端设计

### 4.1 消息状态结构

```jsx
// 流式消息对象
const streamingMessage = {
  id: 'temp_123',
  role: 'assistant',
  content: '',  // 打字机效果逐步填充
  streaming: true,
  status: 'streaming', // 'streaming' | 'done' | 'error'
  agent: 'PlanningAgent',
  model: 'deepseek-chat',
  iteration: 1,
  max_iterations: 10,
  toolCalls: [
    {
      tool: 'search_attractions',
      status: 'running', // 'running' | 'done' | 'error'
      duration_ms: null,
      summary: null,
      error: null,
    }
  ],
  tokenUsage: null,
  reasoningSteps: [],
  contentBuffer: '',
  error: null,
}
```

### 4.2 状态面板 UI（内联展开式）

```
┌─ AI 消息气泡 ──────────────────────────────────────────────┐
│ AI 的回复内容正在打字机效果显示...                           │
└─────────────────────────────────────────────────────────────┘
┌─ 推理过程 (点击展开) ─────────────────────────────────────┐
│ 🤖 PlanningAgent                                          │
│                                                          │
│ 🔧 search_attractions (进行中...)                        │
│ 🔧 budget_calculate (等待中...)                          │
│                                                          │
│ 📊 Token: 150 / 50 / 200 ($0.002)                       │
│ 💭 分析用户偏好：深度体验型                               │
│                                                          │
│ [工具调用结果摘要]                                         │
│ ✅ search_attractions → 找到 12 个景点 (120ms)          │
│ ✅ budget_calculate → 每日预算 ¥500 (45ms)              │
└──────────────────────────────────────────────────────────┘
```

**面板位置：** AI 消息气泡下方，类似现有的 thoughts 展开按钮

**展开触发：** 点击"推理过程"按钮

### 4.3 打字机效果

- 使用 `setInterval` + `performance.now()` 计时
- 每收到 `llm_new_token` 事件，累积到 `contentBuffer`
- 打字速度：约 20ms/字符（可配置）
- 收到 `final` 事件后，直接显示完整内容，停止打字机

### 4.4 EventSource 事件处理

```jsx
const eventHandlers = {
  'agent_switch': (data) => updateMessage(msgId, { agent: data.agent }),
  'model_switch': (data) => updateMessage(msgId, { model: data.model }),
  'iteration': (data) => updateMessage(msgId, { iteration: data.iteration, max_iterations: data.max_iterations }),
  'llm_start': (data) => updateMessage(msgId, { model: data.model }),
  'llm_new_token': (data) => typewriterAppend(msgId, data.token),
  'llm_end': (data) => updateMessage(msgId, { tokenUsage: data }),
  'tool_start': (data) => appendToolCall(msgId, data),
  'tool_end': (data) => updateToolCall(msgId, data.tool, {
    status: 'done',
    summary: data.summary,
    duration_ms: data.duration_ms
  }),
  'tool_error': (data) => updateToolCall(msgId, data.tool, {
    status: 'error',
    error: data.error
  }),
  'token_usage': (data) => updateMessage(msgId, { tokenUsage: data }),
  'reasoning_step': (data) => appendReasoningStep(msgId, data.step),
  'final': (data) => finalizeMessage(msgId, data.answer),
  'error': (data) => handleStreamError(msgId, data),
  'ping': () => {}  // 心跳，无需处理
}
```

**说明：**
- `llm_new_token` 用于逐字打字机效果
- `reasoning_step` 用于展示 LLM 的思考过程（如"分析用户偏好..."）
- `iteration` 更新工具调用循环的当前次数

### 4.5 优雅降级

```
场景 1: 连接中断
├── 已获取内容保留
├── 状态面板显示 "⚠️ 连接中断"
└── 显示 [重新发送] 按钮

场景 2: 模型超时
├── 已获取部分内容保留
├── 状态面板显示 "⏱️ 请求超时"
└── 显示 [重新发送] 按钮

场景 3: 可重试错误 (429)
├── 自动等待 5s 重试
├── 状态面板显示 "🔄 等待配额恢复..."
└── 最多重试 3 次
```

### 4.6 改造文件

| 文件 | 描述 |
|------|------|
| `frontend/src/components/Stage.jsx` | 添加 EventSource 连接、状态面板渲染、打字机效果逻辑 |
| `frontend/src/App.jsx` | 如需扩展流式状态管理（如 streaming state slice），在此添加 |

**状态管理说明：** 当前消息状态通过 `session.messages` 数组管理。流式消息作为特殊消息对象（`streaming: true`）追加到此数组。新增字段（`toolCalls`, `tokenUsage`, `reasoningSteps`, `agent`, `model`, `iteration`）直接添加到消息对象，无需新建独立 state slice。

---

## 5. 数据流

```
用户发送消息
    │
    ▼
EventSource 连接 /api/chat/stream
    │
    ▼
StreamCallbackHandler 初始化
    │
    ▼
ToolCallingService.call_with_tools()
    │
    ├── on_iteration(1, 10) → emit SSE: iteration
    │
    ├── on_tool_start → emit SSE: tool_start
    │
    ├── 执行工具 (120ms)
    │
    ├── on_tool_end → emit SSE: tool_end (摘要)
    │
    ├── on_reasoning_step("分析用户偏好...") → emit SSE: reasoning_step
    │
    └── 继续 LLM 循环...
    │
    ▼
LLM 开始生成
    │
    ├── on_llm_start → emit SSE: llm_start
    │
    ├── on_llm_new_token → emit SSE: llm_new_token (每个 token，打字机)
    │
    ├── on_llm_end → emit SSE: llm_end + token_usage
    │
    ▼ emit SSE: final, {answer: "..."}
```

**说明：**
- `on_reasoning_step` 在每次工具调用结束后、LLM 生成前触发，捕获 LLM 的中间推理过程
- `on_iteration` 在每次工具调用循环开始时触发，`max_iterations` 来自配置（默认 10，可配置）

---

## 6. 错误处理

| 场景 | 处理方式 |
|------|----------|
| SSE 连接断开 | 前端显示"连接中断"，保留已获取内容，显示重连按钮 |
| 工具执行失败 | 发出 `tool_error` 事件，面板显示该工具错误状态 |
| LLM 调用失败 | 发出 `error` 事件，优雅降级显示错误信息 |
| 达到最大迭代次数 | 发出 `error` 事件（reason: "max_iterations"） |
| 可重试错误 (429) | 自动等待 5s 重试，最多 3 次 |

---

## 7. 向后兼容

- 保留现有 `POST /api/chat` 非流式端点
- 新增 `POST /api/chat/stream` SSE 端点
- 前端通过 UI 开关或配置选择使用哪个端点

---

## 8. 实现检查清单

- [ ] `app/api/chat_stream.py` — SSE 端点
- [ ] `app/services/stream_callback.py` — LangChain 风格回调
- [ ] `app/services/stream_manager.py` — 增强事件
- [ ] `app/services/tool_calling_service.py` — 集成回调
- [ ] `app/services/model_router.py` — token 统计
- [ ] `frontend/src/components/Stage.jsx` — 前端流式 UI
