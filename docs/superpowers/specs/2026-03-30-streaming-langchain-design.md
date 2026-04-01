# 流式输出 LangChain 集成设计方案

**日期**：2026-03-30
**状态**：草稿
**负责人**：Claude

## 1. 背景与目标

### 1.1 当前问题

| 问题 | 表现 | 根因 |
|------|------|------|
| 打字机卡顿 | 前端一卡一卡，阻塞输出 | 每个 token 都触发 React 状态更新 |
| Agent 切换不显示 | 前端不知道当前在用哪个 Agent | `agent_switch` 事件从未被正确触发 |
| 工具执行无反馈 | 工具调用时前端无响应 | 工具同步执行，无中间事件 |
| Token 统计为 0 | 看不到消耗 | OpenAI 流式 API 不返回 usage |

### 1.2 改造目标

1. **流畅的打字机效果** - 批量更新，减少渲染频率
2. **实时 Agent/Tool 状态** - 展示当前 Agent、Tool 执行状态
3. **准确的 Token 统计** - 通过 `stream_options` 获取真实 usage
4. **统一的 LangChain 架构** - 可维护、可扩展

---

## 2. 架构设计

### 2.1 目标架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI 后端                              │
│  ┌──────────────┐    ┌──────────────────────────────────────┐  │
│  │ chat_stream  │───▶│         PlanningAgent                │  │
│  │   端点       │    │  ┌────────────────────────────────┐  │  │
│  └──────────────┘    │  │   StreamCallbackHandler        │  │  │
│         │            │  │   (LangChain 风格回调)         │  │  │
│         │            │  └────────────────────────────────┘  │  │
│         │            │           │                           │  │
│         │            │           ▼                           │  │
│         │            │  ┌────────────────────────────────┐  │  │
│         │            │  │      ModelRouter (Runnable)    │  │  │
│         │            │  │   ┌──────────────────────────┐  │  │  │
│         │            │  │   │  ChatOpenAI (DeepSeek)  │  │  │  │
│         │            │  │   │  with fallback chain     │  │  │  │
│         │            │  │   └──────────────────────────┘  │  │  │
│         │            │  └────────────────────────────────┘  │  │
│         │            └──────────────────────────────────────┘  │
│         │                         │                              │
│         ▼                         ▼                              │
│  ┌─────────────────────────────────────────────┐                │
│  │           StreamManager (SSE)                │                │
│  │   发射: agent_switch, tool_start/end,        │                │
│  │         llm_new_token, token_usage, final   │                │
│  └─────────────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ SSE Events
┌─────────────────────────────────────────────────────────────────┐
│                        React 前端                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  EventSource → contentBuffer → 批量渲染 → Typewriter     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  展示面板：                                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 🤖 PlanningAgent → 🔧 search_attractions → ✅ 完成       │   │
│  │ 📊 Tokens: 1200/800/2000 ($0.002)                       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 关键组件变更

| 文件 | 变更类型 | 描述 |
|------|----------|------|
| `app/services/model/model_router.py` | 重构 | 从 SDK 直接调用改为 LangChain Runnable |
| `app/services/streaming/stream_callback.py` | 适配 | 实现 LangChain callback handler 接口 |
| `app/services/streaming/stream_manager.py` | 保持 | SSE 事件发射（改动很小） |
| `app/agents/supervisor.py` | 适配 | 使用新的 callback 机制 |
| `app/tools/budget_tools.py` | 保持 | 工具定义（改动很小） |
| `frontend/src/components/Stage.jsx` | 优化 | token batching + 状态面板增强 |

---

## 3. 详细设计

### 3.1 ModelRouter 重构

**目标**：将直接 SDK 调用改为 LangChain `ChatOpenAI` + `with_fallback` 链。

```python
# app/services/model/model_router.py

from langchain_openai import ChatOpenAI
from langchain_core.callbacks import CallbackManager
from typing import Optional, Any

class ModelRouter:
    def __init__(self):
        self.settings = get_settings()
        self._setup_models()

    def _setup_models(self):
        """初始化模型链（DeepSeek → OpenAI → Claude → Local）。"""
        # 主模型：DeepSeek (OpenAI 兼容)
        self._deepseek = ChatOpenAI(
            model=self.settings.deepseek_model,
            api_key=self.settings.deepseek_api_key,
            base_url=self.settings.deepseek_base_url,
            streaming=True,  # 启用流式
            default_headers={"Authorization": f"Bearer {self.settings.deepseek_api_key}"},
        )

        # Fallback 链将通过 with_fallbacks 实现
        self._fallbacks = []

        # TODO: 添加其他模型的 fallback

    async def call_with_tools(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        stream_callback: Optional[Any] = None,
    ) -> str:
        """带工具调用的模型调用（LangChain 风格）。

        Args:
            messages: 消息列表
            system: 系统提示词
            stream_callback: 流式回调处理器

        Returns:
            LLM 的最终回答文本
        """
        # 转换消息格式
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
        lc_messages = self._convert_messages(messages, system)

        # 构建配置
        config = {"callbacks": [StreamCallbackHandlerAdapter(stream_callback)]} if stream_callback else {}

        # 如果有 tool_calls，使用 with_structured_output 或 tool binding
        # 这里使用简单的 tool prompt 方式（类似当前实现）

        # 执行
        if stream_callback:
            return await self._stream_with_fallback(lc_messages, config)
        else:
            return await self._call_without_stream(lc_messages)

    async def _stream_with_fallback(self, messages, config):
        """流式调用 + fallback。"""
        # 使用基础模型链
        # 失败时自动切换
        # ...
```

**关键点**：
1. 使用 `langchain-openai` 的 `ChatOpenAI`（兼容 DeepSeek）
2. 通过 `with_fallbacks` 实现模型回退
3. 通过 `config["callbacks"]` 注入流式回调

### 3.2 StreamCallbackHandler 适配 LangChain 接口

LangChain 的 callback handler 需要实现特定接口：

```python
# app/services/streaming/stream_callback.py

from langchain_core.callbacks import AsyncCallbackHandler

class LangChainCallbackHandler(AsyncCallbackHandler):
    """LangChain 风格回调处理器（适配 StreamManager）。

    实现以下接口：
    - on_chat_model_start: 发射 llm_start + agent_switch
    - on_llm_new_token: 发射 llm_new_token
    - on_llm_end: 发射 llm_end + token_usage
    - on_tool_start: 发射 tool_start
    - on_tool_end: 发射 tool_end
    """

    def __init__(self, stream_manager: StreamManager, session_id: str):
        self._stream_manager = stream_manager
        self._session_id = session_id
        self._current_agent = "PlanningAgent"

    async def on_chat_model_start(
        self,
        serialized,
        messages,
        *,
        run_id,
        parent_run_id=None,
        **kwargs,
    ):
        """LLM 开始推理。"""
        # 从 messages 推断 agent 名称
        # 发射 agent_switch 事件
        await self._stream_manager.agent_switch(
            self._session_id,
            self._current_agent,
            "LLM 推理中"
        )
        await self._stream_manager.emit(
            self._session_id,
            "llm_start",
            {"model": self._get_model_name(serialized)}
        )

    async def on_llm_new_token(
        self,
        token: str,
        *,
        run_id,
        parent_run_id=None,
        **kwargs,
    ):
        """每个新 token（用于打字机效果）。"""
        await self._stream_manager.emit(
            self._session_id,
            "llm_new_token",
            {"token": token}
        )

    async def on_llm_end(
        self,
        response,
        *,
        run_id,
        parent_run_id=None,
        **kwargs,
    ):
        """LLM 生成完成。"""
        # 从 response 获取 token usage
        usage = getattr(response, "usage_metadata", {}) or {}
        total = usage.get("total_tokens", 0)
        prompt = usage.get("input_tokens", 0)
        completion = usage.get("output_tokens", 0)

        await self._stream_manager.emit(
            self._session_id,
            "llm_end",
            {
                "total_tokens": total,
                "prompt_tokens": prompt,
                "completion_tokens": completion,
                "cost_usd": self._calculate_cost(total),
            }
        )

    async def on_tool_start(
        self,
        serialized,
        input_str,
        *,
        run_id,
        parent_run_id=None,
        **kwargs,
    ):
        """工具开始调用。"""
        tool_name = serialized.get("name", "unknown")
        await self._stream_manager.tool_start(
            self._session_id,
            tool_name,
            str(run_id),
        )

    async def on_tool_end(
        self,
        output,
        *,
        run_id,
        parent_run_id=None,
        **kwargs,
    ):
        """工具调用完成。"""
        # 从 run_id 获取 tool_name（需要另外存储映射）
        summary = self._summarize_output(output)
        duration_ms = 0  # LangChain 不直接提供，需要自己计时
        await self._stream_manager.tool_end(
            self._session_id,
            self._current_tool,
            summary,
            duration_ms,
        )

    def _get_model_name(self, serialized) -> str:
        """从 serialized 获取模型名称。"""
        return serialized.get("id", ["unknown"])[-1]

    def _calculate_cost(self, total_tokens: int) -> float:
        """计算 DeepSeek API 成本。"""
        # DeepSeek 定价：$0.001 per 1K tokens
        return round(total_tokens * 0.001 / 1000, 6)
```

### 3.3 Token 统计增强

通过 `stream_options={"include_usage": true}` 获取真实 usage：

```python
# 在 ModelRouter 中配置

response = await client.chat.completions.create(
    model=self.settings.deepseek_model,
    messages=messages,
    stream=True,
    stream_options={"include_usage": True},  # 关键：获取 usage
)

async for chunk in response:
    if chunk.usage:  # 最后一块包含完整 usage
        total_tokens = chunk.usage.total_tokens
        # ...
```

### 3.4 前端 Token Batching 优化

```javascript
// frontend/src/components/Stage.jsx

// 累积缓冲区，满 10 个 token 或 100ms 后批量更新
const TYPEWRITER_BATCH_SIZE = 10;
const TYPEWRITER_INTERVAL_MS = 100;

useEffect(() => {
  const streamingMsgs = messages.filter(m =>
    m.streaming && m.contentBuffer && m.contentBuffer !== m.content
  );
  if (streamingMsgs.length === 0) return;

  let batchCount = 0;
  const interval = setInterval(() => {
    // 每 100ms 或累积 10 个 token 更新一次
    if (batchCount >= TYPEWRITER_BATCH_SIZE || true) {
      onUpdateMessage(session.id, messages.map(msg => {
        if (msg.streaming && msg.contentBuffer && msg.contentBuffer !== msg.content) {
          return { ...msg, content: msg.contentBuffer };
        }
        return msg;
      }));
      batchCount = 0;
    }
    batchCount++;
  }, TYPEWRITER_INTERVAL_MS);

  return () => clearInterval(interval);
}, [messages, session?.id]);
```

### 3.5 Agent 切换状态面板

```javascript
// 前端展示当前 Agent 执行状态
<div className="streaming-status-panel">
  <div className="streaming-header">
    <span className="agent-name">🤖 {message.currentAgent || 'PlanningAgent'}</span>
    {message.currentSkill && (
      <span className="skill-name">⚙️ {message.currentSkill}</span>
    )}
    <span className={`status-indicator ${message.status}`}>
      {message.status === 'streaming' ? '●' : message.status === 'done' ? '✓' : '!'}
    </span>
  </div>

  {/* 工具调用进度 */}
  {message.toolCalls?.length > 0 && (
    <div className="tool-progress">
      {message.toolCalls.map((tc, i) => (
        <div key={i} className={`tool-item ${tc.status}`}>
          <span className="tool-icon">
            {tc.status === 'running' ? '🔧' : tc.status === 'done' ? '✅' : '❌'}
          </span>
          <span className="tool-name">{tc.tool}</span>
          {tc.status === 'done' && tc.summary && (
            <span className="tool-summary">{tc.summary}</span>
          )}
        </div>
      ))}
    </div>
  )}

  {/* Token 消耗 */}
  {message.tokenUsage && (
    <div className="token-usage">
      📊 Prompt: {message.tokenUsage.prompt_tokens} |
      Completion: {message.tokenUsage.completion_tokens} |
      Total: {message.tokenUsage.total_tokens}
      {message.tokenUsage.cost_usd && ` ($${message.tokenUsage.cost_usd})`}
    </div>
  )}
</div>
```

---

## 4. 实施计划

### 阶段 1：ModelRouter 重构（核心）
1. 安装 `langchain-openai` 依赖
2. 重构 `ModelRouter` 为 LangChain `Runnable`
3. 实现 `fallback` 链（DeepSeek → OpenAI → Claude）
4. 启用 `stream_options={"include_usage": true}`

### 阶段 2：Callback Handler 适配
1. 实现 `LangChainCallbackHandler`
2. 适配 `on_chat_model_start`、`on_llm_new_token` 等接口
3. 保持与现有 `StreamManager` 的兼容

### 阶段 3：Supervisor 适配
1. 更新 `supervisor.py` 使用新的 callback 机制
2. 确保 `trace()` wrapper 正确发射 `agent_switch` 事件

### 阶段 4：前端优化
1. 实现 token batching（减少渲染频率）
2. 增强状态面板展示（Agent、Tool、Token）
3. 优化打字机动画效果

### 阶段 5：测试与调优
1. 手动测试流式输出
2. 验证 token 统计准确性
3. 优化性能（渲染频率、内存占用）

---

## 5. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LangChain 升级导致 API 变更 | 中 | 锁定版本，测试覆盖 |
| DeepSeek API 兼容性 | 低 | 保留 SDK 调用作为 fallback |
| 前端渲染性能 | 中 | token batching + React.memo |
| 现有功能回归 | 中 | 保留原有非流式路径 |

---

## 6. 验收标准

1. ✅ 打字机效果流畅，无明显卡顿
2. ✅ Agent 切换实时显示在状态面板
3. ✅ 工具调用状态（开始/完成）实时显示
4. ✅ Token 消耗统计准确（非 0）
5. ✅ 错误处理（模型失败自动切换）
6. ✅ 保留非流式 fallback 路径
