# Streaming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement SSE-based streaming output with real-time token usage, tool call tracking, and typewriter effect.

**Architecture:** LangChain-style callback handler + StreamManager SSE emitter + FastAPI SSE endpoint + React EventSource frontend.

**Tech Stack:** FastAPI, SSE, React EventSource, asyncio

---

## File Structure

```
app/
├── api/
│   └── chat_stream.py          # [CREATE] SSE streaming endpoint
├── services/
│   ├── stream_callback.py      # [CREATE] LangChain-style callback handler
│   ├── stream_manager.py       # [MODIFY] Already exists, add llm_start, enhance
│   ├── tool_calling_service.py # [MODIFY] Integrate StreamCallback
│   └── model_router.py         # [MODIFY] Add token streaming
frontend/src/
└── components/
    └── Stage.jsx               # [MODIFY] Add EventSource, status panel, typewriter
```

---

## Backend Implementation

### Task 1: Create SSE Endpoint `app/api/chat_stream.py`

**Files:**
- Create: `app/api/chat_stream.py`

- [ ] **Step 1: Write the SSE endpoint skeleton**

```python
"""app/api/chat_stream.py - SSE 流式输出端点。

POST /api/chat/stream
- 请求体同 /api/chat
- 响应: text/event-stream
- 通过 StreamManager 获取 session 对应的事件队列
- 心跳 ping (15s interval)
"""
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import asyncio
import json

from app.services.stream_manager import get_stream_manager
from app.services.chat_service import get_chat_service
from app.config import get_settings

router = APIRouter(prefix="/api", tags=["chat"])


class ChatStreamRequest(BaseModel):
    user_id: str
    message: str
    session_id: str


@router.post("/chat/stream")
async def chat_stream(
    req: ChatStreamRequest,
    background_tasks: BackgroundTasks,
):
    """SSE 流式对话端点。

    流程:
    1. 注册 session 到 StreamManager
    2. 启动后台任务处理 chat
    3. 返回 SSE 事件流
    """
    stream_manager = await get_stream_manager()
    settings = get_settings()

    # 注册 session
    queue = stream_manager.register_session(req.session_id)

    # 启动后台任务处理 chat
    # 注意: BackgroundTasks 必须作为路径操作函数参数传入才会执行
    chat_service = get_chat_service()
    background_tasks.add_task(
        chat_service.chat_stream,
        req.user_id,
        req.session_id,
        req.message,
    )

    # SSE 事件流生成器
    async def event_generator():
        # 发送初始连接事件
        yield f"event: connected\ndata: {{}}\n\n"

        # 心跳间隔 (15s)
        ping_interval = 15

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=ping_interval)
                yield event
            except asyncio.TimeoutError:
                # 发送心跳
                yield f": ping\n\n"
            except GeneratorExit:
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
```

- [ ] **Step 2: Fix SSE data format**

```python
async def sse_generator(session_id: str):
    """SSE 生成器，从 StreamManager 队列读取事件。"""
    stream_manager = await get_stream_manager()
    queue = stream_manager.register_session(session_id)

    # 发送 retry 配置
    yield f"retry: 5000\n\n"

    # 发送连接成功事件 (空 JSON 对象)
    yield f"event: connected\ndata: {{}}\n\n"

    ping_interval = 15
    last_ping = asyncio.get_event_loop().time()

    while True:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=1.0)
            yield event
            last_ping = asyncio.get_event_loop().time()
        except asyncio.TimeoutError:
            # 定期发送心跳
            current_time = asyncio.get_event_loop().time()
            if current_time - last_ping >= ping_interval:
                yield f": heartbeat\n\n"
                last_ping = current_time
```

- [ ] **Step 3: Test endpoint registration**

Run: `cd D:\pychram-workspace\smartJournal && python -c "from app.api.chat_stream import router; print('OK')"`
Expected: OK

- [ ] **Step 4: Commit**

```bash
git add app/api/chat_stream.py
git commit -m "feat: add SSE streaming endpoint /api/chat/stream"
```

---

### Task 2: Create StreamCallback `app/services/stream_callback.py`

**Files:**
- Create: `app/services/stream_callback.py`

- [ ] **Step 1: Write the StreamCallbackHandler class**

```python
"""app/services/stream_callback.py - LangChain 风格回调处理器。

实现以下方法：
- on_llm_start: 发射 llm_start 事件
- on_llm_new_token: 发射 llm_new_token 事件（用于打字机效果）
- on_llm_end: 发射 llm_end + token_usage 事件
- on_tool_start: 发射 tool_start 事件
- on_tool_end: 发射 tool_end 事件（结果截取为摘要）
- on_reasoning_step: 发射 reasoning_step 事件（LLM 思考过程）
- on_iteration: 发射 iteration 事件（工具调用循环次数）
"""
import json
from typing import Any, Optional


class StreamCallbackHandler:
    """LangChain 风格回调处理器。

    通过 __init__ 注入 StreamManager 实例和 session_id。
    """

    def __init__(self, stream_manager, session_id: str):
        self._stream_manager = stream_manager
        self._session_id = session_id
        self._iteration = 0
        self._max_iterations = 10

    async def on_llm_start(self, model: str) -> None:
        """LLM 开始推理。"""
        await self._stream_manager.emit(
            self._session_id,
            "llm_start",
            {"model": model}
        )

    async def on_llm_new_token(self, token: str) -> None:
        """每个新 token（用于打字机效果）。"""
        await self._stream_manager.emit(
            self._session_id,
            "llm_new_token",
            {"token": token}
        )

    async def on_llm_end(
        self,
        total_tokens: int,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        """LLM 生成完成。"""
        # 计算成本 (DeepSeek 近似单价)
        cost_per_token = 0.001 / 1000  # $0.001 per 1K tokens
        cost_usd = total_tokens * cost_per_token

        await self._stream_manager.emit(
            self._session_id,
            "llm_end",
            {
                "total_tokens": total_tokens,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost_usd": round(cost_usd, 6),
            }
        )

    async def on_tool_start(
        self,
        tool: str,
        tool_call_id: str,
    ) -> None:
        """工具开始调用。"""
        await self._stream_manager.tool_start(
            self._session_id,
            tool,
            tool_call_id,
        )

    async def on_tool_end(
        self,
        tool: str,
        tool_result: Any,
        duration_ms: int,
    ) -> None:
        """工具调用完成。

        将完整结果截取为摘要。
        """
        summary = self._summarize_result(tool_result)
        await self._stream_manager.tool_end(
            self._session_id,
            tool,
            summary,
            duration_ms,
        )

    async def on_tool_error(
        self,
        tool: str,
        error: str,
    ) -> None:
        """工具执行失败。"""
        await self._stream_manager.tool_error(
            self._session_id,
            tool,
            error,
        )

    async def on_reasoning_step(self, step: str) -> None:
        """发射 LLM 推理步骤。"""
        await self._stream_manager.reasoning_step(
            self._session_id,
            step,
        )

    async def on_iteration(self, iteration: int) -> None:
        """发射工具调用循环次数。"""
        self._iteration = iteration
        await self._stream_manager.iteration(
            self._session_id,
            iteration,
            self._max_iterations,
        )

    async def on_agent_switch(self, agent: str) -> None:
        """Agent 切换。"""
        await self._stream_manager.agent_switch(self._session_id, agent)

    async def on_model_switch(self, model: str, reason: str) -> None:
        """模型切换。"""
        await self._stream_manager.model_switch(
            self._session_id,
            model,
            reason,
        )

    async def on_error(self, error: str, recoverable: bool = True) -> None:
        """错误。"""
        await self._stream_manager.error(
            self._session_id,
            error,
        )

    async def on_final(self, answer: str) -> None:
        """最终回复。"""
        await self._stream_manager.final(self._session_id, answer)

    def _summarize_result(self, result: Any, max_length: int = 100) -> str:
        """将工具结果截取为摘要。

        避免 SSE 传输过大数据。
        """
        if result is None:
            return "无结果"

        if isinstance(result, str):
            summary = result
        elif isinstance(result, dict):
            # 提取关键字段作为摘要
            if "items" in result and isinstance(result["items"], list):
                summary = f"找到 {len(result['items'])} 个结果"
            elif "budget" in result:
                summary = f"预算 ¥{result.get('budget', 'N/A')}"
            elif "total" in result:
                summary = f"总计 ¥{result.get('total', 'N/A')}"
            else:
                summary = str(result)[:max_length]
        elif isinstance(result, list):
            summary = f"共 {len(result)} 项"
        else:
            summary = str(result)[:max_length]

        if len(summary) > max_length:
            summary = summary[:max_length] + "..."

        return summary
```

- [ ] **Step 2: Write basic test**

```python
# tests/services/test_stream_callback.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.stream_callback import StreamCallbackHandler


@pytest.fixture
def mock_stream_manager():
    manager = MagicMock()
    manager.emit = AsyncMock()
    manager.tool_start = AsyncMock()
    manager.tool_end = AsyncMock()
    manager.reasoning_step = AsyncMock()
    manager.iteration = AsyncMock()
    return manager


@pytest.fixture
def handler(mock_stream_manager):
    return StreamCallbackHandler(mock_stream_manager, "test_session")


@pytest.mark.asyncio
async def test_on_llm_new_token(handler, mock_stream_manager):
    await handler.on_llm_new_token("你")
    mock_stream_manager.emit.assert_called_once_with(
        "test_session",
        "llm_new_token",
        {"token": "你"}
    )


@pytest.mark.asyncio
async def test_on_tool_end_summarizes_list_result(handler, mock_stream_manager):
    result = {"items": [{"name": "景点1"}, {"name": "景点2"}]}
    await handler.on_tool_end("search_attractions", result, 120)
    mock_stream_manager.tool_end.assert_called_once_with(
        "test_session",
        "search_attractions",
        "找到 2 个结果",
        120,
    )
```

- [ ] **Step 3: Run tests**

Run: `cd D:\pychram-workspace\smartJournal && python -m pytest tests/services/test_stream_callback.py -v`
Expected: PASS (or FAIL if test file doesn't exist yet - that's expected)

- [ ] **Step 4: Commit**

```bash
git add app/services/stream_callback.py tests/services/test_stream_callback.py
git commit -m "feat: add StreamCallbackHandler for LangChain-style callbacks"
```

---

### Task 3: Enhance StreamManager `app/services/stream_manager.py`

**Files:**
- Modify: `app/services/stream_manager.py` (already exists)

**Status:** Most events already exist. Need to verify `llm_start`, `llm_end` events are present.

- [ ] **Step 1: Check existing events in stream_manager.py**

Read `app/services/stream_manager.py` and verify these methods exist:
- `llm_start` / `emit` with "llm_start"
- `llm_end` / `emit` with "llm_end"
- `llm_new_token` / `emit` with "llm_new_token"

- [ ] **Step 2: Add missing events if needed**

If `llm_start` or `llm_end` methods don't exist, add them:

```python
async def llm_start(self, session_id: str, model: str) -> None:
    await self.emit(session_id, "llm_start", {"model": model})

async def llm_end(
    self,
    session_id: str,
    total_tokens: int,
    prompt_tokens: int,
    completion_tokens: int,
) -> None:
    await self.emit(
        session_id,
        "llm_end",
        {
            "total_tokens": total_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }
    )
```

- [ ] **Step 2b: Fix tool_end key name**

The existing `tool_end` method emits with key `"result"`, but the frontend expects `"summary"`. Fix the existing `tool_end` method:

```python
# Current (wrong):
async def tool_end(
    self,
    session_id: str,
    tool: str,
    result: Any,  # Wrong key name
    duration_ms: int
) -> None:
    await self.emit(
        session_id, "tool_end",
        {"tool": tool, "result": result, "duration_ms": duration_ms}
    )

# Fixed:
async def tool_end(
    self,
    session_id: str,
    tool: str,
    summary: Any,  # Correct key name per spec
    duration_ms: int
) -> None:
    await self.emit(
        session_id, "tool_end",
        {"tool": tool, "summary": summary, "duration_ms": duration_ms}
    )
```

- [ ] **Step 3: Test the stream manager**

```bash
cd D:\pychram-workspace\smartJournal && python -c "
import asyncio
from app.services.stream_manager import StreamManager

async def test():
    sm = StreamManager()
    queue = sm.register_session('test')
    await sm.llm_start('test', 'deepseek-chat')
    print('llm_start emitted')

asyncio.run(test())
"
```

Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add app/services/stream_manager.py
git commit -m "feat: enhance StreamManager with llm_start and llm_end events"
```

---

### Task 4: Integrate StreamCallback into ToolCallingService

**Files:**
- Modify: `app/services/tool_calling_service.py`

- [ ] **Step 1: Add StreamCallback integration**

Modify `ToolCallingService.call_with_tools()` to:
1. Accept optional `stream_callback` parameter
2. Emit `iteration` at start of each loop
3. Emit `tool_start` before executing tool
4. Pass `stream_callback` to `_execute_tool_call`

```python
# In call_with_tools method, add:
if stream_callback:
    await stream_callback.on_iteration(iteration)
    for tool_call in tool_calls:
        await stream_callback.on_tool_start(
            tool_call["function"]["name"],
            tool_call["id"]
        )
        # Pass callback to _execute_tool_call for error handling
        tool_result = await self._execute_tool_call(tool_call, stream_callback)
        # Note: on_tool_end is called inside _execute_tool_call on success
```

- [ ] **Step 2: Modify _execute_tool_call to accept callback**

```python
async def _execute_tool_call(
    self,
    tool_call: Dict[str, Any],
    stream_callback: Optional[Any] = None,
) -> Any:
    """Execute single tool call with optional streaming callback."""
    # ... existing logic (parse args, get tool) ...

    try:
        # ... existing execution logic ...

        # Notify callback on success (only here, NOT in the loop)
        if stream_callback:
            await stream_callback.on_tool_end(func_name, result, duration_ms)

        return result
    except Exception as e:
        # Notify callback on error
        if stream_callback:
            await stream_callback.on_tool_error(func_name, str(e))
        return {"success": False, "error": str(e)}
```

**IMPORTANT:** The callback is called ONLY inside `_execute_tool_call`, not in the outer loop. This avoids double-calling.

- [ ] **Step 3: Update call_with_tools signature**

```python
async def call_with_tools(
    self,
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    model: str = "openai",
    stream_callback: Optional[Any] = None,
) -> str:
```

- [ ] **Step 4: Write test for streaming integration**

```python
# tests/services/test_tool_calling_service.py
# Add test_streaming_callback test

@pytest.mark.asyncio
async def test_streaming_callback_on_tool_calls():
    """Verify streaming callbacks are emitted during tool execution."""
    # ... setup mock callback ...
    # ... call call_with_tools with a tool ...
    # ... verify callback methods were called ...
```

- [ ] **Step 5: Run tests**

Run: `cd D:\pychram-workspace\smartJournal && python -m pytest tests/services/test_tool_calling_service.py -v`

- [ ] **Step 6: Commit**

```bash
git add app/services/tool_calling_service.py tests/services/test_tool_calling_service.py
git commit -m "feat: integrate StreamCallback into ToolCallingService"
```

---

### Task 5: Enhance ModelRouter for Token Streaming

**Files:**
- Modify: `app/services/model_router.py`

- [ ] **Step 1: Add stream callback to _call_openai_with_tools**

Modify `_call_openai_with_tools` to:
1. Accept `stream_callback` parameter
2. Emit `llm_start` before LLM call
3. Stream tokens via `llm_new_token` callback (if using streaming)
4. Pass `stream_callback` to ToolCallingService
5. Emit `llm_end` with token counts after completion

```python
async def _call_openai_with_tools(
    self,
    messages: List[Dict[str, Any]],
    system: str,
    stream_callback: Optional[Any] = None,
) -> str:
    """使用 Tool Calling 调用 OpenAI 兼容 API with streaming."""

    # ... existing setup (create client, insert system message, get tools) ...

    # Emit llm_start
    if stream_callback:
        await stream_callback.on_llm_start(self.settings.deepseek_model)

    # Use streaming if callback provided
    if stream_callback:
        # For streaming with tool calls, we need to handle chunks carefully
        # First, do a non-streaming call to get tool_calls, then stream content
        # OR use streaming but buffer until we see if there are tool_calls

        # Approach: Use streaming for content only, handle tool_calls separately
        response = await client.chat.completions.create(
            model=self.settings.deepseek_model,
            messages=messages,
            tools=tools if tools else None,
            stream=True,
        )

        accumulated_content = ""
        final_chunk = None  # Keep last chunk to check for tool_calls

        async for chunk in response:
            final_chunk = chunk
            if chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                accumulated_content += token
                await stream_callback.on_llm_new_token(token)

        # After streaming, parse tool_calls from final chunk
        tool_calls = None
        if final_chunk and hasattr(final_chunk.choices[0], 'message') and final_chunk.choices[0].message.tool_calls:
            tool_calls = [
                {"id": tc.id, "type": tc.type, "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in final_chunk.choices[0].message.tool_calls
            ]

        assistant_msg = {
            "role": "assistant",
            "content": accumulated_content,
        }
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls

        messages.append(assistant_msg)

        # If there are tool_calls, execute them via ToolCallingService
        # with the same stream_callback
        if tool_calls:
            # Re-use non-streaming tool execution for tool calls
            # The ToolCallingService will handle callbacks
            return await self._execute_tool_calls_with_callback(
                messages, model, stream_callback
            )

        # Emit llm_end with token counts (from usage if available)
        usage = getattr(response, 'usage', None) or {}
        if stream_callback:
            await stream_callback.on_llm_end(
                total_tokens=usage.get('total_tokens', 0),
                prompt_tokens=usage.get('prompt_tokens', 0),
                completion_tokens=usage.get('completion_tokens', 0),
            )

        return accumulated_content
    else:
        # Non-streaming (existing behavior via ToolCallingService)
        return await self._call_openai_with_tools_non_streaming(messages, system)
```

**Note:** The streaming path handles tool_calls by:
1. Streaming the response content token by token
2. If tool_calls appear in the final chunk, delegate to `_execute_tool_calls_with_callback`
3. The ToolCallingService will execute tools and emit callbacks

- [ ] **Step 2: Add helper method for tool call execution with callback**

```python
async def _execute_tool_calls_with_callback(
    self,
    messages: List[Dict[str, Any]],
    model: str,
    stream_callback,
) -> str:
    """Execute tool calls via ToolCallingService with streaming callback."""
    tc_service = get_tool_calling_service()
    # Pass stream_callback to ToolCallingService
    return await tc_service.call_with_tools(
        messages=messages,
        tools=get_tools_schema(),
        model=model,
        stream_callback=stream_callback,  # Pass callback through
    )
```

- [ ] **Step 3: Update call_with_tools to pass callback to _call_openai_with_tools**

```python
async def call_with_tools(
    self,
    messages: List[Dict[str, Any]],
    system: str = "",
    stream_callback: Optional[Any] = None,
) -> str:
    """带工具调用的模型调用 with optional streaming."""

    chain = self.settings.model_chain_list
    last_error = None

    for model in chain:
        try:
            if model == "openai":
                return await self._call_openai_with_tools(
                    messages, system, stream_callback
                )
            # ... other models ...
```

- [ ] **Step 3: Test**

```bash
cd D:\pychram-workspace\smartJournal && python -c "
from app.services.model_router import get_model_router
router = get_model_router()
print('ModelRouter loaded OK')
"
```

- [ ] **Step 4: Commit**

```bash
git add app/services/model_router.py
git commit -m "feat: add token streaming to ModelRouter"
```

---

### Task 6: Add chat_stream Method to ChatService

**Files:**
- Modify: `app/services/chat_service.py`

- [ ] **Step 1: Add chat_stream method**

```python
async def chat_stream(
    self,
    user_id: str,
    session_id: str,
    message: str,
) -> None:
    """处理流式对话请求（后台任务）。

    替代 chat() 方法，将事件通过 StreamManager 发射。
    """
    from app.services.stream_callback import StreamCallbackHandler
    from app.services.stream_manager import get_stream_manager

    stream_manager = await get_stream_manager()
    callback = StreamCallbackHandler(stream_manager, session_id)

    # 1. 动态加载 system prompt
    prompt_result = self._prompt_loader.invoke({
        "user_id": user_id,
        "session_id": session_id,
    })
    system_prompt = prompt_result["system_prompt"]

    # 2. 加载记忆
    session_memory = await self._injector.load_session_memory(
        user_id=user_id,
        session_id=session_id,
        mode="main",
    )

    # 3. 获取对话历史
    mem = self._memory_manager.get_memory(session_id)
    history = mem.get_history()
    formatted_history = self._format_history(history)

    # 4. 构建完整 system message
    memory_section = f"\n\n## Memory\n\n{session_memory}" if session_memory else ""
    full_system = f"{system_prompt}{memory_section}\n\n## 对话历史\n{formatted_history}" if formatted_history else f"{system_prompt}{memory_section}"

    # 5. 构建消息列表
    chat_messages = []
    if full_system:
        chat_messages.append({"role": "system", "content": full_system})
    chat_messages.append({"role": "user", "content": message})

    # 6. 调用模型（带 streaming）
    try:
        answer = await self._router.call_with_tools(
            messages=chat_messages,
            system="",
            stream_callback=callback,
        )

        # 7. 发射最终回复
        await callback.on_final(answer)

        # 8. 保存到记忆
        mem.save_context({"input": message}, {"output": answer})
        self._daily_writer.append(
            session_id=session_id,
            user_id=user_id,
            human_message=message,
            ai_message=answer,
        )

    except Exception as e:
        await callback.on_error(str(e), recoverable=False)
```

- [ ] **Step 2: Test chat_stream method**

```bash
cd D:\pychram-workspace\smartJournal && python -c "
import asyncio
from app.services.chat_service import get_chat_service

async def test():
    svc = get_chat_service()
    print('ChatService loaded OK')

asyncio.run(test())
"
```

- [ ] **Step 3: Commit**

```bash
git add app/services/chat_service.py
git commit -m "feat: add chat_stream method to ChatService"
```

---

## Frontend Implementation

### Task 7: Implement Streaming UI in Stage.jsx

**Files:**
- Modify: `frontend/src/components/Stage.jsx`

- [ ] **Step 1: Add streaming state and refs**

```jsx
// Add to Stage component
const [streamingMsgId, setStreamingMsgId] = useState(null)
const eventSourceRef = useRef(null)
const typewriterRef = useRef(null)
```

- [ ] **Step 2: Add streaming message creation**

```jsx
const createStreamingMessage = (sessionId) => {
  return {
    id: `temp_${Date.now()}`,
    role: 'assistant',
    content: '',
    streaming: true,
    status: 'streaming',
    agent: 'PlanningAgent',
    model: '',
    iteration: 0,
    max_iterations: 10,
    toolCalls: [],
    tokenUsage: null,
    reasoningSteps: [],
    contentBuffer: '',
    error: null,
  }
}
```

- [ ] **Step 3: Add EventSource connection function**

```jsx
const startStreaming = (sessionId, messageId) => {
  // Connect to SSE endpoint
  const es = new EventSource(`/api/chat/stream?session_id=${sessionId}`)
  eventSourceRef.current = es

  // Set up all event handlers
  es.addEventListener('connected', () => {
    console.log('SSE connected')
  })

  es.addEventListener('llm_new_token', (e) => {
    const { token } = JSON.parse(e.data)
    // Typewriter effect
    setMessages(prev => prev.map(msg =>
      msg.id === messageId
        ? { ...msg, contentBuffer: msg.contentBuffer + token }
        : msg
    ))
  })

  es.addEventListener('tool_start', (e) => {
    const { tool, tool_call_id } = JSON.parse(e.data)
    setMessages(prev => prev.map(msg =>
      msg.id === messageId
        ? {
            ...msg,
            toolCalls: [...msg.toolCalls, { tool, tool_call_id, status: 'running' }]
          }
        : msg
    ))
  })

  es.addEventListener('tool_end', (e) => {
    const { tool, summary, duration_ms } = JSON.parse(e.data)
    setMessages(prev => prev.map(msg =>
      msg.id === messageId
        ? {
            ...msg,
            toolCalls: msg.toolCalls.map(tc =>
              tc.tool === tool
                ? { ...tc, status: 'done', summary, duration_ms }
                : tc
            )
          }
        : msg
    ))
  })

  es.addEventListener('token_usage', (e) => {
    const usage = JSON.parse(e.data)
    setMessages(prev => prev.map(msg =>
      msg.id === messageId
        ? { ...msg, tokenUsage: usage }
        : msg
    ))
  })

  es.addEventListener('reasoning_step', (e) => {
    const { step } = JSON.parse(e.data)
    setMessages(prev => prev.map(msg =>
      msg.id === messageId
        ? { ...msg, reasoningSteps: [...msg.reasoningSteps, step] }
        : msg
    ))
  })

  es.addEventListener('iteration', (e) => {
    const { iteration, max_iterations } = JSON.parse(e.data)
    setMessages(prev => prev.map(msg =>
      msg.id === messageId
        ? { ...msg, iteration, max_iterations }
        : msg
    ))
  })

  es.addEventListener('agent_switch', (e) => {
    const { agent } = JSON.parse(e.data)
    setMessages(prev => prev.map(msg =>
      msg.id === messageId
        ? { ...msg, agent }
        : msg
    ))
  })

  es.addEventListener('final', (e) => {
    const { answer } = JSON.parse(e.data)
    setMessages(prev => prev.map(msg =>
      msg.id === messageId
        ? { ...msg, content: answer, streaming: false, status: 'done' }
        : msg
    ))
    es.close()
  })

  es.addEventListener('error', (e) => {
    const { error } = JSON.parse(e.data)
    setMessages(prev => prev.map(msg =>
      msg.id === messageId
        ? { ...msg, error, streaming: false, status: 'error' }
        : msg
    ))
    es.close()
  })
}
```

- [ ] **Step 4: Modify handleSubmit to use streaming**

```jsx
const handleSubmit = async (e) => {
  e.preventDefault()
  if (!input.trim() || isLoading || !session) return

  const userMessage = {
    id: Date.now().toString(),
    role: 'user',
    content: input.trim(),
    timestamp: new Date().toISOString()
  }

  // Create streaming message
  const assistantMessage = createStreamingMessage(session.id)
  setStreamingMsgId(assistantMessage.id)

  const newMessages = [...session.messages, userMessage, assistantMessage]
  onUpdateMessage(session.id, newMessages)
  setInput('')
  setIsLoading(true)

  // Start SSE connection
  startStreaming(session.id, assistantMessage.id)

  try {
    // Send to API (non-blocking for streaming)
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: 'default_user',
        session_id: session.id,
        message: input.trim()
      }),
    })

    if (!response.ok) {
      throw new Error('Stream failed')
    }
    // Response body is consumed by EventSource
  } catch (error) {
    // Handle error
    setMessages(prev => prev.map(msg =>
      msg.id === assistantMessage.id
        ? { ...msg, content: '连接失败', streaming: false, status: 'error' }
        : msg
    ))
  } finally {
    setIsLoading(false)
  }
}
```

- [ ] **Step 5: Add streaming status panel UI**

```jsx
// Inside message bubble, after ReactMarkdown
{message.streaming && (
  <div className="streaming-status-panel">
    <div className="streaming-header">
      <span className="agent-name">🤖 {message.agent}</span>
      {message.model && <span className="model-name">via {message.model}</span>}
    </div>

    {message.toolCalls.length > 0 && (
      <div className="tool-calls">
        {message.toolCalls.map((tc, i) => (
          <div key={i} className={`tool-call ${tc.status}`}>
            <span className="tool-icon">
              {tc.status === 'running' ? '🔧' : tc.status === 'done' ? '✅' : '❌'}
            </span>
            <span className="tool-name">{tc.tool}</span>
            {tc.status === 'done' && tc.summary && (
              <span className="tool-summary">→ {tc.summary}</span>
            )}
            {tc.status === 'done' && tc.duration_ms && (
              <span className="tool-duration">({tc.duration_ms}ms)</span>
            )}
          </div>
        ))}
      </div>
    )}

    {message.tokenUsage && (
      <div className="token-usage">
        📊 Token: {message.tokenUsage.prompt_tokens} / {message.tokenUsage.completion_tokens} / {message.tokenUsage.total_tokens}
        {message.tokenUsage.cost_usd && ` ($${message.tokenUsage.cost_usd})`}
      </div>
    )}

    {message.reasoningSteps.length > 0 && (
      <div className="reasoning-steps">
        {message.reasoningSteps.map((step, i) => (
          <div key={i} className="reasoning-step">💭 {step}</div>
        ))}
      </div>
    )}

    {message.error && (
      <div className="stream-error">
        ⚠️ {message.error}
        <button onClick={() => retryStream(message.id)}>重新发送</button>
      </div>
    )}
  </div>
)}
```

- [ ] **Step 6: Add CSS for streaming panel**

Add to `frontend/src/index.css` or component styles:

```css
.streaming-status-panel {
  background: rgba(0, 0, 0, 0.05);
  border-radius: 8px;
  padding: 12px;
  margin-top: 8px;
  font-size: 13px;
}

.streaming-header {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.agent-name {
  font-weight: 600;
}

.tool-calls {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}

.tool-call {
  display: flex;
  align-items: center;
  gap: 4px;
}

.tool-call.running .tool-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.token-usage {
  color: #666;
  font-size: 12px;
  margin-bottom: 8px;
}

.reasoning-steps {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.reasoning-step {
  color: #888;
  font-size: 12px;
}
```

- [ ] **Step 7: Test frontend build**

Run: `cd D:\pychram-workspace\smartJournal\frontend && npm run build`
Expected: Build succeeds without errors

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/Stage.jsx frontend/src/index.css
git commit -m "feat: add streaming UI with EventSource and status panel"
```

---

## Integration Task

### Task 8: End-to-End Integration Test

- [ ] **Step 1: Verify all imports work**

```bash
cd D:\pychram-workspace\smartJournal && python -c "
from app.api.chat_stream import router
from app.services.stream_callback import StreamCallbackHandler
from app.services.stream_manager import get_stream_manager
print('All imports OK')
"
```

- [ ] **Step 2: Start backend and test SSE endpoint**

Run: `cd D:\pychram-workspace\smartJournal && python -m uvicorn app.main:app --reload`
Check: Visit http://localhost:8000/docs and verify `/api/chat/stream` endpoint exists

- [ ] **Step 3: Test from frontend**

Start frontend: `cd frontend && npm run dev`
Send a message and verify streaming events appear in browser DevTools Network tab

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | SSE Endpoint | `app/api/chat_stream.py` |
| 2 | StreamCallback | `app/services/stream_callback.py` |
| 3 | StreamManager Enhancement | `app/services/stream_manager.py` |
| 4 | ToolCallingService Integration | `app/services/tool_calling_service.py` |
| 5 | ModelRouter Token Streaming | `app/services/model_router.py` |
| 6 | ChatService chat_stream | `app/services/chat_service.py` |
| 7 | Frontend Streaming UI | `frontend/src/components/Stage.jsx` |
| 8 | E2E Integration Test | - |
