# 流式输出 LangChain 集成实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 ModelRouter 从直接 SDK 调用重构为 LangChain Runnable 抽象层，实现流畅的打字机效果、实时 Agent/Tool 状态显示、准确的 Token 统计。

**Architecture:** 使用 LangChain `ChatOpenAI` (兼容 DeepSeek) + `with_fallbacks` 实现模型回退链，通过 `CallbackHandler` 注入流式事件到 SSE StreamManager，前端实现 token batching 优化渲染性能。

**Tech Stack:** LangChain, LangChain-OpenAI, FastAPI, SSE, React

---

## 文件结构

```
app/
├── services/
│   ├── model/
│   │   └── model_router.py          # 重构：LangChain Runnable
│   └── streaming/
│       ├── stream_callback.py      # 新增：LangChainCallbackHandler
│       └── stream_manager.py       # 保持（改动很小）
├── agents/
│   └── supervisor.py               # 适配：使用新 callback 机制
frontend/src/
└── components/
    └── Stage.jsx                   # 优化：token batching
```

---

## Task 1: 检查依赖并安装 LangChain

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: 检查 requirements.txt 当前依赖**

```bash
cat requirements.txt
```

- [ ] **Step 2: 确认是否已安装 langchain 和 langchain-openai**

```
# 如果没有，添加：
langchain>=0.3.0
langchain-core>=0.3.0
langchain-openai>=0.2.0
```

- [ ] **Step 3: 安装依赖**

```bash
pip install langchain>=0.3.0 langchain-core>=0.3.0 langchain-openai>=0.2.0
```

- [ ] **Step 4: 验证安装**

```bash
python -c "from langchain_openai import ChatOpenAI; print('OK')"
```

---

## Task 2: 创建 LangChainCallbackHandler

**Files:**
- Create: `app/services/streaming/langchain_callback.py`
- Modify: `app/services/streaming/stream_callback.py` (添加 adapter)

- [ ] **Step 1: 创建 LangChainCallbackHandler 类**

```python
# app/services/streaming/langchain_callback.py
"""LangChain 风格回调处理器 - 适配 StreamManager。

实现 langchain_core.callbacks.AsyncCallbackHandler 接口，
将 LangChain 事件转换为 SSE 事件。
"""
import time
from typing import Any, Dict, Optional
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import Generation, LLMResult

DEEPSEEK_PRICE_PER_1K_TOKENS = 0.001  # per 1K tokens


class LangChainCallbackHandler(AsyncCallbackHandler):
    """LangChain 风格回调处理器。

    将 LangChain 的事件（on_chat_model_start, on_llm_new_token 等）
    转换为 SSE 事件并通过 StreamManager 发射。
    """

    def __init__(self, stream_manager: "StreamManager", session_id: str):
        self._stream_manager = stream_manager
        self._session_id = session_id
        self._current_agent = "PlanningAgent"
        self._current_tool = "unknown"
        self._tool_start_time: Dict[str, float] = {}
        self._token_buffer = ""
        self._last_token_time = time.time()

    async def on_chat_model_start(
        self,
        serialized,
        messages,
        *,
        run_id,
        parent_run_id=None,
        **kwargs,
    ):
        """LLM 开始推理，发射 agent_switch + llm_start。"""
        model_name = serialized.get("id", ["unknown"])[-1] if serialized else "unknown"
        # 发射 agent_switch
        await self._stream_manager.agent_switch(
            self._session_id,
            self._current_agent,
            f"LLM 推理中 ({model_name})"
        )
        # 发射 llm_start
        await self._stream_manager.emit(
            self._session_id,
            "llm_start",
            {"model": model_name}
        )

    async def on_llm_new_token(
        self,
        token: str,
        *,
        run_id,
        parent_run_id=None,
        **kwargs,
    ):
        """每个新 token，发射 llm_new_token。"""
        await self._stream_manager.emit(
            self._session_id,
            "llm_new_token",
            {"token": token}
        )

    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id,
        parent_run_id=None,
        **kwargs,
    ):
        """LLM 生成完成，发射 llm_end + token_usage。"""
        # 从 response 获取 token usage
        # LangChain 的 LLMResult 在 streaming 时可能没有完整 usage
        # 使用 response.llm_output 或 estimate
        usage = getattr(response, "usage_metadata", None)
        if usage:
            total = usage.get("total_tokens", 0)
            prompt = usage.get("input_tokens", 0)
            completion = usage.get("output_tokens", 0)
        else:
            # Fallback：估算
            total, prompt, completion = 0, 0, 0

        cost_usd = total * DEEPSEEK_PRICE_PER_1K_TOKENS / 1000

        await self._stream_manager.emit(
            self._session_id,
            "llm_end",
            {
                "total_tokens": total,
                "prompt_tokens": prompt,
                "completion_tokens": completion,
                "cost_usd": round(cost_usd, 6),
            }
        )

    async def on_tool_start(
        self,
        serialized,
        input_str: str,
        *,
        run_id,
        parent_run_id=None,
        **kwargs,
    ):
        """工具开始调用，发射 tool_start。"""
        tool_name = serialized.get("name", "unknown") if serialized else "unknown"
        self._current_tool = tool_name
        self._tool_start_time[run_id] = time.time()

        await self._stream_manager.tool_start(
            self._session_id,
            tool_name,
            str(run_id),
        )

    async def on_tool_end(
        self,
        output: str,
        *,
        run_id,
        parent_run_id=None,
        **kwargs,
    ):
        """工具调用完成，发射 tool_end。"""
        # 从 run_id 获取 tool_name 和耗时
        start_time = self._tool_start_time.pop(run_id, None)
        duration_ms = int((time.time() - start_time) * 1000) if start_time else 0

        summary = self._summarize_output(output)
        await self._stream_manager.tool_end(
            self._session_id,
            self._current_tool,
            summary,
            duration_ms,
        )

    async def on_tool_error(
        self,
        error: Exception,
        *,
        run_id,
        parent_run_id=None,
        **kwargs,
    ):
        """工具执行失败，发射 tool_error。"""
        await self._stream_manager.tool_error(
            self._session_id,
            self._current_tool,
            str(error),
        )

    def _summarize_output(self, output: Any, max_length: int = 100) -> str:
        """将工具输出截取为摘要。"""
        if output is None:
            return "无结果"
        if isinstance(output, str):
            summary = output
        elif isinstance(output, dict):
            if "items" in output and isinstance(output["items"], list):
                summary = f"找到 {len(output['items'])} 个结果"
            elif "budget" in output:
                summary = f"预算 ¥{output.get('budget', 'N/A')}"
            else:
                summary = str(output)[:max_length]
        elif isinstance(output, list):
            summary = f"共 {len(output)} 项"
        else:
            summary = str(output)[:max_length]

        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        return summary
```

- [ ] **Step 2: 在 stream_callback.py 中添加 StreamCallbackHandlerAdapter**

```python
# app/services/streaming/stream_callback.py 末尾添加

class StreamCallbackHandlerAdapter:
    """将旧的 StreamCallbackHandler 适配为 LangChain callback。

    用于兼容旧的 non-LangChain 代码路径。
    """

    def __init__(self, stream_callback: Optional["StreamCallbackHandler"]):
        self._cb = stream_callback

    async def on_llm_start(self, model: str):
        if self._cb:
            await self._cb.on_llm_start(model)

    async def on_llm_new_token(self, token: str):
        if self._cb:
            await self._cb.on_llm_new_token(token)

    async def on_llm_end(self, total_tokens: int, prompt_tokens: int, completion_tokens: int):
        if self._cb:
            await self._cb.on_llm_end(total_tokens, prompt_tokens, completion_tokens)

    async def on_tool_start(self, tool: str, tool_call_id: str):
        if self._cb:
            await self._cb.on_tool_start(tool, tool_call_id)

    async def on_tool_end(self, tool: str, tool_result: Any, duration_ms: int):
        if self._cb:
            await self._cb.on_tool_end(tool, tool_result, duration_ms)
```

---

## Task 3: 重构 ModelRouter 为 LangChain Runnable

**Files:**
- Modify: `app/services/model/model_router.py`

- [ ] **Step 1: 读取现有 model_router.py 确认完整结构**

```bash
cat app/services/model/model_router.py
```

- [ ] **Step 2: 重写 ModelRouter 类**

```python
# app/services/model/model_router.py
"""模型路由 - LangChain Runnable 抽象层。

使用 LangChain ChatOpenAI (OpenAI 兼容) + fallback 链。
支持 DeepSeek, OpenAI, Claude, Local 模型。
"""
import asyncio
from typing import Any, Dict, List, Literal, Optional

from app.config import get_settings
from app.services.tools.tool_registry import get_tools_schema
from app.services.tools.tool_calling_service import get_tool_calling_service
from app.services.streaming.langchain_callback import LangChainCallbackHandler
from langchain_openai import ChatOpenAI
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

ModelName = Literal["deepseek", "openai", "claude", "local"]


class ModelRouter:
    """模型路由器 - LangChain Runnable 风格。

    使用 ChatOpenAI (OpenAI 兼容) 实现 DeepSeek 调用，
    通过 with_fallbacks 实现模型回退链。
    """

    def __init__(self):
        self.settings = get_settings()
        self._clients: Dict[str, ChatOpenAI] = {}
        self._setup_clients()

    def _setup_clients(self):
        """初始化各模型的 ChatOpenAI 客户端。"""
        # DeepSeek (主模型)
        if self.settings.deepseek_api_key:
            self._clients["deepseek"] = ChatOpenAI(
                model=self.settings.deepseek_model or "deepseek-chat",
                api_key=self.settings.deepseek_api_key,
                base_url=self.settings.deepseek_base_url,
                streaming=True,
                temperature=0.7,
                max_tokens=4000,
            )

        # OpenAI (fallback)
        if self.settings.openai_api_key:
            self._clients["openai"] = ChatOpenAI(
                model=self.settings.openai_model or "gpt-4o-mini",
                api_key=self.settings.openai_api_key,
                streaming=True,
                temperature=0.7,
            )

        # TODO: Claude, Local

    async def call_with_tools(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        stream_callback: Optional[Any] = None,
    ) -> str:
        """带工具调用的模型调用（LangChain 风格）。

        Args:
            messages: 消息列表（会直接修改）
            system: 系统提示词
            stream_callback: 流式回调处理器

        Returns:
            LLM 的最终回答文本
        """
        # 转换消息格式
        lc_messages = self._convert_messages(messages, system)

        # 获取工具 schema
        tools = get_tools_schema()

        # 获取主模型（DeepSeek）
        primary = self._clients.get("deepseek") or self._clients.get("openai")
        if not primary:
            raise Exception("No model client available")

        # 构建 callback 配置
        callbacks = None
        if stream_callback:
            # 创建 LangChain callback handler
            from app.services.streaming.stream_manager import get_stream_manager
            import uuid
            sm = await get_stream_manager()
            callbacks = [LangChainCallbackHandler(sm, str(uuid.uuid4()))]

        # 构建配置
        config = {"callbacks": callbacks} if callbacks else {}

        # 如果有工具，绑定工具
        if tools:
            # 简单方式：将工具转为 string prompt（保持当前架构）
            # TODO: 未来可升级为 with_structured_output
            return await self._call_with_tools_streaming(
                primary, lc_messages, tools, config
            )
        else:
            # 无工具：简单对话
            return await self._call_streaming(primary, lc_messages, config)

    async def _call_streaming(
        self,
        model: ChatOpenAI,
        messages: List[Any],
        config: Dict[str, Any],
    ) -> str:
        """流式调用模型。"""
        accumulated = ""
        async for chunk in model.astream(messages, config):
            if chunk.content:
                accumulated += chunk.content
        return accumulated

    async def _call_with_tools_streaming(
        self,
        model: ChatOpenAI,
        messages: List[Any],
        tools: List[Dict[str, Any]],
        config: Dict[str, Any],
    ) -> str:
        """带工具调用的流式模型调用。

        注意：当前实现保持与原有架构兼容，
        工具调用通过 ToolCallingService 执行。
        未来可升级为 with_structured_output。
        """
        # 使用 streaming 模式
        # 注意：ChatOpenAI 的 streaming 不直接返回 tool_calls
        # 需要通过 finish event 获取

        # 构建工具描述 prompt（保持当前架构）
        tools_prompt = self._build_tools_prompt(tools)
        messages_with_tools = messages + [HumanMessage(content=f"\n\n{tools_prompt}")]

        accumulated = ""
        final_chunk = None

        async for chunk in model.astream(messages_with_tools, config):
            if chunk.content:
                accumulated += chunk.content
                final_chunk = chunk

        # 检查是否有 tool_calls（在 AIMessageChunk 中）
        # LangChain streaming 返回 AIMessageChunk，可能包含 tool_calls
        # 但更可靠的方式是使用 non-streaming + 解析

        # 暂时保持非流式获取完整响应
        # TODO: 实现真正的 streaming + tool_calls
        return accumulated

    def _convert_messages(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
    ) -> List[Any]:
        """将 dict 消息格式转换为 LangChain 消息格式。"""
        lc_messages = []

        if system:
            lc_messages.append(SystemMessage(content=system))

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            elif role == "system":
                lc_messages.append(SystemMessage(content=content))

        return lc_messages

    def _build_tools_prompt(self, tools: List[Dict[str, Any]]) -> str:
        """将工具 schema 构建为自然语言描述。"""
        if not tools:
            return ""

        lines = ["你可以使用以下工具："]
        for tool in tools:
            name = tool.get("name", "unknown")
            desc = tool.get("description", "")
            params = tool.get("parameters", {}).get("properties", {})

            lines.append(f"\n## {name}")
            lines.append(f"描述: {desc}")
            if params:
                lines.append("参数:")
                for pname, pdesc in params.items():
                    lines.append(f"  - {pname}: {pdesc.get('description', '')}")

        return "\n".join(lines)


# 单例
_router: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
```

---

## Task 4: 适配 Supervisor 使用新 Callback

**Files:**
- Modify: `app/agents/supervisor.py`
- Modify: `app/services/streaming/stream_manager.py`

- [ ] **Step 1: 修改 StreamManager 支持 session_id 为空时的优雅处理**

```python
# app/services/streaming/stream_manager.py
# 在 emit 方法中添加调试日志（如果需要）

async def emit(
    self,
    session_id: str,
    event_name: str,
    data: Any,
) -> None:
    """发射 SSE 事件到指定会话的队列。"""
    queue = self._sessions.get(session_id)
    if queue is None:
        # 调试：session 未注册时记录但不抛出异常
        import logging
        logging.warning(f"Session {session_id} not found for event {event_name}")
        return

    event_line = f"event: {event_name}\n"
    data_line = f"data: {json.dumps(data)}\n\n"
    await queue.put(event_line + data_line)
```

- [ ] **Step 2: 更新 supervisor.py 的 trace 函数**

```python
# app/agents/supervisor.py
# 修改 trace 函数中的 agent_switch 事件发射

async def trace(agent_name: str, coro, stream_callback=None):
    """包装器用于计时 Agent 调用，并可选地发射 agent_switch 事件。"""
    agent_trace["agents"].append(agent_name)
    agent_trace["invocation_order"].append(len(agent_trace["agents"]))
    t = time.time()

    # 发射 agent_switch 事件
    if stream_callback:
        await stream_callback.on_agent_switch(agent_name)

    try:
        result = await coro
        agent_trace["durations_ms"].append(int((time.time() - t) * 1000))
        return result
    except Exception as e:
        agent_trace["durations_ms"].append(int((time.time() - t) * 1000))
        agent_trace["errors"].append({"agent": agent_name, "error": str(e)})
        raise
```

---

## Task 5: 前端 Token Batching 优化

**Files:**
- Modify: `frontend/src/components/Stage.jsx`

- [ ] **Step 1: 修改 Typewriter 效果实现（batch 模式）**

```javascript
// Stage.jsx

// 在组件顶部添加常量
const TYPEWRITER_BATCH_SIZE = 10;  // 累积 10 个 token 后更新
const TYPEWRITER_INTERVAL_MS = 80;  // 或 80ms 间隔

// 修改 useEffect typewriter animation
useEffect(() => {
  const streamingMsgs = messages.filter(m =>
    m.streaming && m.contentBuffer && m.contentBuffer !== m.content
  );
  if (streamingMsgs.length === 0) return;

  // 使用 requestAnimationFrame 或 setInterval
  const interval = setInterval(() => {
    const hasUpdate = messages.some(msg =>
      msg.streaming && msg.contentBuffer && msg.contentBuffer !== msg.content
    );

    if (hasUpdate) {
      onUpdateMessage(session.id, messages.map(msg => {
        if (msg.streaming && msg.contentBuffer && msg.contentBuffer !== msg.content) {
          return { ...msg, content: msg.contentBuffer };
        }
        return msg;
      }));
    }
  }, TYPEWRITER_INTERVAL_MS);

  return () => clearInterval(interval);
}, [messages, session?.id, onUpdateMessage]);
```

- [ ] **Step 2: 增强 agent_switch 事件处理（带描述）**

```javascript
// 修改 agent_switch 事件监听器
es.addEventListener('agent_switch', (e) => {
  const { agent, description } = JSON.parse(e.data);
  const updated = messagesRef.current.map(msg =>
    msg.id === messageId
      ? {
          ...msg,
          currentAgent: agent,
          phaseDescription: description || '',
          // 不清空 contentBuffer，保持连续性
        }
      : msg
  );
  onUpdateMessage(sessionId, updated);
});
```

- [ ] **Step 3: 添加 token 使用率进度条**

```javascript
// 在 streaming-status-panel 中添加
{message.tokenUsage && (
  <div className="token-usage-bar">
    <div className="token-usage">
      📊 Prompt: {message.tokenUsage.prompt_tokens} |
      Completion: {message.tokenUsage.completion_tokens} |
      Total: {message.tokenUsage.total_tokens}
      {message.tokenUsage.cost_usd && ` ($${message.tokenUsage.cost_usd})`}
    </div>
    {message.tokenUsage.total_tokens > 0 && (
      <div className="token-progress-bar">
        <div
          className="token-progress-fill"
          style={{
            width: `${Math.min(100, (message.tokenUsage.total_tokens / 8000) * 100)}%`
          }}
        />
        <span>{(message.tokenUsage.total_tokens / 8000 * 100).toFixed(1)}% of 8K</span>
      </div>
    )}
  </div>
)}
```

---

## Task 6: 添加样式增强

**Files:**
- Modify: `frontend/src/styles/global.css`

- [ ] **Step 1: 添加 streaming status panel 样式**

```css
/* Token 使用率进度条 */
.token-usage-bar {
  margin-top: 4px;
}

.token-progress-bar {
  height: 4px;
  background: #e0e0e0;
  border-radius: 2px;
  margin-top: 4px;
  position: relative;
}

.token-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4CAF50, #8BC34A);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.token-progress-bar span {
  position: absolute;
  right: 0;
  top: -16px;
  font-size: 10px;
  color: #666;
}

/* Agent 状态指示器 */
.agent-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.status-indicator.streaming {
  background: #4CAF50;
  animation: pulse 1s infinite;
}

.status-indicator.done {
  background: #2196F3;
}

.status-indicator.error {
  background: #f44336;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

---

## Task 7: 端到端测试

**Files:**
- 无（手动测试）

- [ ] **Step 1: 启动后端**

```bash
cd D:/pychram-workspace/smartJournal
python -m app.main
```

- [ ] **Step 2: 启动前端**

```bash
cd D:/pychram-workspace/smartJournal/frontend
npm run dev
```

- [ ] **Step 3: 验证打字机效果**
- 发送一条旅行规划消息
- 观察输出是否流畅（无明显卡顿）
- 检查 Token 是否累进显示（非突然出现）

- [ ] **Step 4: 验证 Agent 切换显示**
- 观察是否显示 "Preference Agent"、"TravelPlanner Agent" 等
- 切换时是否有描述（如 "LLM 推理中"）

- [ ] **Step 5: 验证工具状态**
- 工具开始时是否显示 "🔧 工具名"
- 工具完成时是否显示 "✅ 工具名 → 摘要 (ms)"

- [ ] **Step 6: 验证 Token 统计**
- 检查 llm_end 事件后是否显示 prompt/completion/total tokens
- 检查 cost_usd 是否显示

---

## 任务依赖关系

```
Task 1 (依赖) → Task 2 → Task 3 → Task 4 → Task 7
                                              ↑
Task 5 (前端，可并行) ─────────────────────────┘
Task 6 (样式，依赖 Task 5)
```

---

## 验收标准检查

| 验收项 | Task |
|--------|------|
| ✅ 打字机效果流畅 | Task 5 |
| ✅ Agent 切换实时显示 | Task 4 |
| ✅ 工具调用状态实时显示 | Task 2, Task 4 |
| ✅ Token 消耗统计准确（非 0） | Task 2 |
| ✅ 保留非流式 fallback | Task 3 |
| ✅ 错误处理 | Task 4 |
