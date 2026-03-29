# Streaming SSE Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement real-time streaming of LLM reasoning state to the frontend via SSE, including tool call tracking, token usage, and typewriter effect.

**Architecture:**
- `StreamManager` singleton holds `asyncio.Queue` per session; services emit events to it, SSE endpoint consumes and streams to client
- Background task runs chat logic and emits events to the queue; SSE response reads from queue concurrently
- Tool calls and token usage events are emitted from `ToolCallingService` and `ModelRouter` during execution

**Tech Stack:** FastAPI StreamingResponse, asyncio.Queue, Server-Sent Events, React EventSource

---

## File Structure

```
app/
├── services/
│   └── stream_manager.py     # NEW: SSE event emitter singleton
├── api/
│   ├── chat_stream.py        # NEW: SSE streaming endpoint
│   └── __init__.py           # MODIFY: add chat_stream router
├── services/
│   └── tool_calling_service.py  # MODIFY: emit SSE events
│   └── model_router.py       # MODIFY: expose token usage
└── main.py                   # MODIFY: register chat_stream router

frontend/src/components/
└── Stage.jsx                 # MODIFY: EventSource + state panel + typewriter
```

---

## Task 1: StreamManager — SSE Event Emitter

**Files:**
- Create: `app/services/stream_manager.py`
- Test: `tests/services/test_stream_manager.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/services/test_stream_manager.py
import pytest
from app.services.stream_manager import StreamManager, get_stream_manager

def test_singleton():
    sm1 = get_stream_manager()
    sm2 = get_stream_manager()
    assert sm1 is sm2

def test_register_unregister_session():
    sm = get_stream_manager()
    session_id = "test-session-1"
    queue = sm.register_session(session_id)
    assert queue is not None
    sm.unregister_session(session_id)

@pytest.mark.asyncio
async def test_emit_and_get():
    sm = get_stream_manager()
    session_id = "test-session-2"
    sm.register_session(session_id)
    await sm.emit(session_id, "test_event", {"key": "value"})
    result = await sm.get_event(session_id)
    assert "event: test_event" in result
    assert '"key": "value"' in result
    sm.unregister_session(session_id)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/services/test_stream_manager.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal StreamManager implementation**

```python
# app/services/stream_manager.py
"""app/services/stream_manager.py - SSE 事件发射器单例。

维护每个 session_id -> asyncio.Queue 的映射，供各服务发射 SSE 事件。
"""
import asyncio
import json
from typing import Any, Dict, Optional


class StreamManager:
    """SSE 事件发射器。

    单例模式。每个 session_id 对应一个 asyncio.Queue。
    发射事件时，将格式化后的 SSE 数据放入对应队列。
    SSE 端点从队列中读取并推送给客户端。
    """

    def __init__(self):
        self._sessions: Dict[str, asyncio.Queue] = {}
        self._lock = asyncio.Lock()

    def register_session(self, session_id: str) -> asyncio.Queue:
        """注册一个会话，返回其事件队列。"""
        if session_id not in self._sessions:
            self._sessions[session_id] = asyncio.Queue()
        return self._sessions[session_id]

    def unregister_session(self, session_id: str) -> None:
        """注销一个会话，清理其队列。"""
        self._sessions.pop(session_id, None)

    async def emit(
        self,
        session_id: str,
        event_name: str,
        data: Any,
    ) -> None:
        """发射 SSE 事件到指定会话的队列。

        Args:
            session_id: 会话 ID
            event_name: 事件名（如 'tool_start'）
            data: 事件数据（会被 JSON 序列化）
        """
        queue = self._sessions.get(session_id)
        if queue is None:
            return

        event_line = f"event: {event_name}\n"
        data_line = f"data: {json.dumps(data)}\n\n"
        await queue.put(event_line + data_line)

    async def emit_comment(self, session_id: str, comment: str) -> None:
        """发射 SSE comment（用于心跳等）。"""
        queue = self._sessions.get(session_id)
        if queue is None:
            return
        await queue.put(f": {comment}\n\n")

    async def get_event(self, session_id: str) -> Optional[str]:
        """从队列获取事件（阻塞等待）。超时返回 None。"""
        queue = self._sessions.get(session_id)
        if queue is None:
            return None
        try:
            return await asyncio.wait_for(queue.get(), timeout=60.0)
        except asyncio.TimeoutError:
            return None

    # ---- 便捷方法 ----

    async def agent_switch(self, session_id: str, agent: str) -> None:
        await self.emit(session_id, "agent_switch", {"agent": agent})

    async def model_switch(
        self, session_id: str, model: str, reason: str
    ) -> None:
        await self.emit(session_id, "model_switch", {"model": model, "reason": reason})

    async def iteration(
        self, session_id: str, iteration: int, max_iterations: int
    ) -> None:
        await self.emit(
            session_id, "iteration",
            {"iteration": iteration, "max_iterations": max_iterations}
        )

    async def tool_start(
        self, session_id: str, tool: str, tool_call_id: str
    ) -> None:
        await self.emit(
            session_id, "tool_start",
            {"tool": tool, "tool_call_id": tool_call_id}
        )

    async def tool_end(
        self, session_id: str, tool: str, result: Any, duration_ms: int
    ) -> None:
        await self.emit(
            session_id, "tool_end",
            {"tool": tool, "result": result, "duration_ms": duration_ms}
        )

    async def tool_error(self, session_id: str, tool: str, error: str) -> None:
        await self.emit(
            session_id, "tool_error",
            {"tool": tool, "error": error}
        )

    async def token_usage(
        self, session_id: str,
        prompt_tokens: int, completion_tokens: int, total_tokens: int
    ) -> None:
        await self.emit(
            session_id, "token_usage",
            {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            }
        )

    async def reasoning_step(self, session_id: str, step: str) -> None:
        await self.emit(session_id, "reasoning_step", {"step": step})

    async def content_chunk(self, session_id: str, content: str) -> None:
        await self.emit(session_id, "content_chunk", {"content": content})

    async def final(self, session_id: str, answer: str) -> None:
        await self.emit(session_id, "final", {"answer": answer})

    async def error(self, session_id: str, error: str) -> None:
        await self.emit(session_id, "error", {"error": error})

    async def ping(self, session_id: str) -> None:
        await self.emit_comment(session_id, "ping")


# 单例
_stream_manager: Optional[StreamManager] = None


def get_stream_manager() -> StreamManager:
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = StreamManager()
    return _stream_manager
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/services/test_stream_manager.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/stream_manager.py tests/services/test_stream_manager.py
git commit -m "feat: add StreamManager SSE event emitter singleton"
```

---

## Task 2: SSE Streaming Endpoint

**Files:**
- Create: `app/api/chat_stream.py`
- Modify: `app/api/__init__.py` — add router import
- Modify: `app/main.py` — include chat_stream router

- [ ] **Step 1: Write the SSE endpoint skeleton**

```python
# app/api/chat_stream.py
"""app/api/chat_stream.py - SSE 流式聊天端点。

POST /api/chat/stream — 接收消息，通过 SSE 流式返回推理状态。
"""
import asyncio
import json
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from app.services.stream_manager import get_stream_manager
from app.services.chat_service import get_chat_service
from app.config import get_settings

router = APIRouter(prefix="/api", tags=["chat"])


class ChatStreamRequest(BaseModel):
    user_id: str
    message: str
    session_id: str


async def event_generator(session_id: str, user_id: str, message: str):
    """生成 SSE 事件流。

    1. 注册 session 到 StreamManager
    2. 启动后台任务处理聊天
    3. 从队列读取事件并 yeild
    4. 结束时发送 final 或 error
    """
    sm = get_stream_manager()
    queue = sm.register_session(session_id)

    async def background_chat():
        """后台运行聊天逻辑，发射事件到 StreamManager。"""
        try:
            chat_service = get_chat_service()
            # TODO: 后续集成到 chat_service 内部
            # 目前 emit 硬编码示例事件用于测试
            await sm.tool_start(session_id, "search_attractions", "call_001")
            await asyncio.sleep(0.5)
            await sm.tool_end(
                session_id, "search_attractions",
                {"success": True, "count": 12}, 120
            )
            await sm.token_usage(session_id, 100, 50, 150)
            await sm.content_chunk(session_id, "正在为你规划行程...")
            await asyncio.sleep(0.5)
            await sm.final(session_id, "这是一个测试回复。")
        except Exception as e:
            await sm.error(session_id, str(e))
        finally:
            sm.unregister_session(session_id)

    # 启动心跳任务
    async def heartbeat():
        while True:
            await asyncio.sleep(15)
            try:
                await sm.ping(session_id)
            except Exception:
                break

    # 启动后台任务
    chat_task = asyncio.create_task(background_chat())
    heartbeat_task = asyncio.create_task(heartbeat())

    try:
        # 从队列读取事件直到 session 注销
        while True:
            event = await queue.get()
            yield event
            # 检查是否结束
            if event.startswith("event: final\n") or event.startswith("event: error\n"):
                break
    except Exception:
        pass
    finally:
        chat_task.cancel()
        heartbeat_task.cancel()


@router.post("/api/chat/stream")
async def chat_stream(req: ChatStreamRequest):
    """SSE 流式聊天端点。

    连接建立后，通过 SSE 流式推送推理状态（工具调用、token 使用等）。
    前端通过 EventSource 消费这些事件并实时更新 UI。
    """
    return StreamingResponse(
        event_generator(req.session_id, req.user_id, req.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx buffering
        }
    )
```

- [ ] **Step 2: Register the router**

Modify `app/api/__init__.py` — add `chat_stream` to imports:
```python
from app.api import chat, chat_stream, plan, preference, monitor, session, workspace, skills
```

- [ ] **Step 3: Include router in main.py**

Modify `app/main.py` line 9 — add `chat_stream` to imports, and add `app.include_router(chat_stream.router)` after line 52.

- [ ] **Step 4: Test the endpoint manually**

Run: `python -m uvicorn app.main:app --reload --port 8000`
Then in browser console or curl:
```bash
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","session_id":"test-001","message":"规划北京3日游"}'
```
You should see SSE events in the response.

- [ ] **Step 5: Commit**

```bash
git add app/api/chat_stream.py app/api/__init__.py app/main.py
git commit -m "feat: add SSE streaming endpoint POST /api/chat/stream"
```

---

## Task 3: Integrate StreamManager into ToolCallingService

**Files:**
- Modify: `app/services/tool_calling_service.py`

- [ ] **Step 1: Update __init__ to accept StreamManager**

Modify `ToolCallingService.__init__` to accept an optional `stream_manager` parameter and store it.

- [ ] **Step 2: Add session_id to call_with_tools**

Update `call_with_tools` signature to accept `session_id: Optional[str] = None`. Pass it down to `_execute_tool_call`.

- [ ] **Step 3: Emit tool_start and tool_end events**

In `_execute_tool_call`:
- At start: emit `tool_start` with tool name and tool_call_id
- At end: emit `tool_end` with result and duration_ms
- On error: emit `tool_error`

- [ ] **Step 4: Emit iteration event**

In `call_with_tools` while loop: emit `iteration` event each iteration.

```python
# In call_with_tools while loop (add after iteration += 1):
if self._stream_manager and session_id:
    await self._stream_manager.iteration(session_id, iteration, self._max_iterations)
```

- [ ] **Step 5: Commit**

```bash
git add app/services/tool_calling_service.py
git commit -m "feat: emit SSE events during tool execution"
```

---

## Task 4: Expose Token Usage from ModelRouter

**Files:**
- Modify: `app/services/model_router.py`

- [ ] **Step 1: Return token usage from _call_openai**

Modify `_call_openai` to return a tuple `(content: str, usage: dict)` instead of just content. The usage dict should contain `prompt_tokens`, `completion_tokens`, `total_tokens`.

- [ ] **Step 2: Propagate token usage up the call chain**

Update `_call_llm`, `call_with_tools`, and `call` to optionally return token usage. The caller (`chat_service.chat` or streaming background task) can then emit `token_usage` events.

- [ ] **Step 3: Emit token_usage event via StreamManager**

In the streaming background task (Task 2 Step 1's background_chat), after calling the LLM, emit `token_usage` event.

- [ ] **Step 4: Commit**

```bash
git add app/services/model_router.py
git commit -m "feat: expose token usage from model router"
```

---

## Task 5: Wire ChatService into Streaming

**Files:**
- Modify: `app/services/chat_service.py` — add streaming variant
- Modify: `app/api/chat_stream.py` — use actual ChatService

- [ ] **Step 1: Add chat_stream method to ChatService**

Add a `chat_stream(self, user_id, session_id, message)` method that:
1. Loads system prompt and memory (like `chat()`)
2. Uses `ToolCallingService.call_with_tools()` with stream_manager
3. Emits `content_chunk` events as content arrives
4. Returns final answer

- [ ] **Step 2: Update background_chat in chat_stream.py**

Replace the mock `background_chat` with a call to `chat_service.chat_stream()`.

- [ ] **Step 3: Emit reasoning_step events**

In `ChatService.chat_stream`, after key reasoning milestones, emit `reasoning_step` events.

- [ ] **Step 4: Commit**

```bash
git add app/services/chat_service.py app/api/chat_stream.py
git commit -m "feat: integrate ChatService with SSE streaming"
```

---

## Task 6: Frontend — Stage.jsx Streaming UI

**Files:**
- Modify: `frontend/src/components/Stage.jsx`

- [ ] **Step 1: Add streaming state fields to message object**

The message object should gain: `streaming: boolean`, `status: 'streaming'|'done'|'error'`, `agent: string`, `toolCalls: array`, `tokenUsage: object`, `reasoningSteps: array`.

- [ ] **Step 2: Add startStreaming function**

```javascript
const startStreaming = (sessionId, userId, message) => {
  const tempMessage = {
    id: `temp_${Date.now()}`,
    role: 'assistant',
    content: '',
    streaming: true,
    status: 'streaming',
    agent: null,
    toolCalls: [],
    tokenUsage: null,
    reasoningSteps: [],
  }

  // Append placeholder message
  const newMessages = [...session.messages, tempMessage]
  onUpdateMessage(session.id, newMessages)

  // Connect SSE
  const es = new EventSource(
    `/api/chat/stream?session_id=${sessionId}&user_id=${userId}`
  )

  es.addEventListener('agent_switch', (e) => {
    updateMessage(tempMessage.id, { agent: JSON.parse(e.data).agent })
  })

  es.addEventListener('tool_start', (e) => {
    const { tool, tool_call_id } = JSON.parse(e.data)
    appendToolCall(tempMessage.id, { tool, tool_call_id, status: 'running' })
  })

  es.addEventListener('tool_end', (e) => {
    const { tool, result, duration_ms } = JSON.parse(e.data)
    updateToolCall(tempMessage.id, tool, { status: 'done', result, duration_ms })
  })

  es.addEventListener('tool_error', (e) => {
    const { tool, error } = JSON.parse(e.data)
    updateToolCall(tempMessage.id, tool, { status: 'error', error })
  })

  es.addEventListener('token_usage', (e) => {
    updateMessage(tempMessage.id, { tokenUsage: JSON.parse(e.data) })
  })

  es.addEventListener('reasoning_step', (e) => {
    appendReasoningStep(tempMessage.id, JSON.parse(e.data).step)
  })

  es.addEventListener('content_chunk', (e) => {
    const { content } = JSON.parse(e.data)
    typewriterAppend(tempMessage.id, content)
  })

  es.addEventListener('final', (e) => {
    const { answer } = JSON.parse(e.data)
    finalizeMessage(tempMessage.id, answer)
    es.close()
  })

  es.addEventListener('error', (e) => {
    handleStreamError(tempMessage.id, JSON.parse(e.data).error)
    es.close()
  })

  es.addEventListener('ping', () => {}) // heartbeat, no-op

  return es
}
```

- [ ] **Step 3: Implement helper functions**

```javascript
const updateMessage = (id, patch) => {
  const messages = session.messages.map(m =>
    m.id === id ? { ...m, ...patch } : m
  )
  onUpdateMessage(session.id, messages)
}

const appendToolCall = (msgId, toolCall) => {
  updateMessage(msgId, { toolCalls: [...(session.messages.find(m => m.id === msgId)?.toolCalls || []), toolCall] })
}

const updateToolCall = (msgId, toolName, patch) => {
  const msg = session.messages.find(m => m.id === msgId)
  if (!msg) return
  const toolCalls = msg.toolCalls.map(tc =>
    tc.tool === toolName ? { ...tc, ...patch } : tc
  )
  updateMessage(msgId, { toolCalls })
}

const appendReasoningStep = (msgId, step) => {
  const msg = session.messages.find(m => m.id === msgId)
  if (!msg) return
  updateMessage(msgId, { reasoningSteps: [...(msg.reasoningSteps || []), step] })
}

// Typewriter effect
const typewriterAppend = (msgId, chunk) => {
  const msg = session.messages.find(m => m.id === msgId)
  if (!msg) return
  // Accumulate in content, UI renders incrementally via CSS animation
  updateMessage(msgId, { content: msg.content + chunk })
}

const finalizeMessage = (msgId, answer) => {
  updateMessage(msgId, { content: answer, streaming: false, status: 'done' })
}

const handleStreamError = (msgId, error) => {
  updateMessage(msgId, { content: `错误: ${error}`, streaming: false, status: 'error' })
}
```

- [ ] **Step 4: Add streaming status panel UI**

In the assistant message rendering (inside `displayMessages.map`), add a status panel below the message bubble when `message.streaming || message.toolCalls?.length > 0`:

```jsx
{message.role === 'assistant' && (
  <>
    <div className="message-bubble">
      <ReactMarkdown>{message.content}</ReactMarkdown>
    </div>

    {/* Status Panel */}
    {(message.streaming || message.toolCalls?.length > 0 || message.agent) && (
      <div className="streaming-status-panel">
        {message.agent && (
          <div className="status-agent">🤖 {message.agent}</div>
        )}
        {message.toolCalls?.map((tc, i) => (
          <div key={i} className={`status-tool status-tool-${tc.status}`}>
            {tc.status === 'running' && '🔧 '}
            {tc.status === 'done' && '✅ '}
            {tc.status === 'error' && '❌ '}
            {tc.tool}
            {tc.status === 'done' && tc.duration_ms && ` (${tc.duration_ms}ms)`}
          </div>
        ))}
        {message.tokenUsage && (
          <div className="status-token">
            📊 Token: {message.tokenUsage.prompt_tokens} / {message.tokenUsage.completion_tokens} / {message.tokenUsage.total_tokens}
          </div>
        )}
        {message.reasoningSteps?.map((step, i) => (
          <div key={i} className="status-reasoning">💭 {step}</div>
        ))}
        {message.streaming && (
          <div className="status-streaming">📝 {message.content || '正在思考...'}</div>
        )}
      </div>
    )}
  </>
)}
```

- [ ] **Step 5: Add CSS styles**

Add to `frontend/src/styles/Stage.css`:

```css
.streaming-status-panel {
  background: rgba(0, 0, 0, 0.05);
  border-radius: 8px;
  padding: 8px 12px;
  margin-top: 8px;
  font-size: 12px;
  color: #666;
}

.status-agent {
  font-weight: bold;
  margin-bottom: 4px;
}

.status-tool {
  padding: 2px 0;
}

.status-tool-running {
  color: #f59e0b;
}

.status-tool-done {
  color: #22c55e;
}

.status-tool-error {
  color: #ef4444;
}

.status-token {
  color: #8b5cf6;
}

.status-reasoning {
  color: #6b7280;
  font-style: italic;
}

.status-streaming {
  color: #3b82f6;
}
```

- [ ] **Step 6: Switch handleSubmit to use streaming**

Replace the `fetch('/api/chat', ...)` call in `handleSubmit` with a call to `startStreaming(session.id, 'default_user', input.trim())`. Remove the `isLoading` wait for the response since streaming is async.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/Stage.jsx frontend/src/styles/Stage.css
git commit -m "feat(frontend): add SSE streaming UI with status panel and typewriter effect"
```

---

## Spec Coverage Check

| Spec Requirement | Task |
|------------------|------|
| SSE endpoint POST /api/chat/stream | Task 2 |
| StreamManager singleton | Task 1 |
| tool_start / tool_end events | Task 3 |
| tool_error event | Task 3 |
| iteration event | Task 3 |
| token_usage event | Task 4 |
| reasoning_step event | Task 5 |
| content_chunk event | Task 5 |
| final / error events | Task 5 |
| ping heartbeat | Task 2 |
| Frontend EventSource | Task 6 |
| Status panel UI | Task 6 |
| Typewriter effect | Task 6 |
| Backward compatible (keep POST /api/chat) | All tasks |

All spec items are covered.

---

## Type Consistency Check

- `StreamManager.emit(session_id, event_name, data)` — `session_id` is `str` throughout
- `tool_start({tool, tool_call_id})` — consistent with spec
- `tool_end({tool, result, duration_ms})` — consistent with spec
- `token_usage({prompt_tokens, completion_tokens, total_tokens})` — consistent with spec
- Frontend `EventSource` URL uses `session_id` and `user_id` query params — matches spec
