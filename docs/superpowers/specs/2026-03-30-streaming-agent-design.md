# 流式 Agent 执行可视化设计方案

**日期**: 2026-03-30
**状态**: 已批准
**目标**: 前端流式输出，打字机效果，实时展示 Agent/Skill/Token 消耗

---

## 1. 背景与目标

当前流式输出存在 `agent_switch` 事件从未被触发的问题，导致前端无法展示当前执行到了哪个 Agent。

**目标效果**：
- 打字机式流式输出
- 实时展示当前 Agent（如 PreferenceAgent）
- 实时展示当前 Skill/Tool（如 search_attractions）
- 实时滚动 Token 消耗（prompt/completion/total）
- 新 Agent 接管时清空前一个 Agent 的输出

---

## 2. 架构概览

```
User Message → chat_stream_post()
                    ↓
            chat_service.chat_stream(stream_callback)
                    ↓
            Supervisor.plan(callback)
                ↓
            [agent_switch event: "PreferenceAgent"]
                ↓
            [skill_start: "search_attractions"]
                ↓
            [skill_end: "找到 5 个景点" (230ms)]
                ↓
            [agent_switch: "BudgetAgent"]
                ↓
            [llm_new_token: "已为您规划..."]
                ↓
            [llm_end: {tokens, cost}]
```

---

## 3. 事件定义

| 事件名 | 载荷 | 触发时机 |
|--------|------|----------|
| `agent_switch` | `{agent: string}` | 新 Agent 开始执行 |
| `skill_start` | `{skill: string, tool_call_id: string}` | 工具/Skill 开始 |
| `skill_end` | `{skill: string, summary: string, duration_ms: number}` | 工具/Skill 结束 |
| `llm_new_token` | `{token: string}` | LLM 输出 token（打字机） |
| `llm_end` | `{total_tokens, prompt_tokens, completion_tokens, cost_usd}` | LLM 结束 |

---

## 4. 改动清单

### 4.1 `app/services/stream_callback.py`

扩展 `StreamCallbackHandler`，新增方法：

```python
async def on_phase_start(self, phase: str, description: str) -> None:
    """Agent 阶段开始。"""
    await self._stream_manager.emit(self._session_id, "agent_switch", {
        "agent": phase,
        "description": description,
    })
```

### 4.2 `app/services/stream_manager.py`

新增便捷方法（已部分存在，确认完整）：

```python
async def skill_start(self, session_id, skill, tool_call_id): ...
async def skill_end(self, session_id, skill, summary, duration_ms): ...
```

### 4.3 `app/agents/supervisor.py`

在 `PlanningAgent.plan()` 中注入回调，各阶段执行时触发：

```python
# 阶段1：PreferenceAgent
await self._stream_callback.on_phase_start("PreferenceAgent", "解析用户偏好")
pref_result = await self.pref_agent.parse_and_update(user_id, message)

# 阶段2：并行搜索
await self._stream_callback.on_phase_start("TravelPlanner", "搜索景点和餐厅")

# 阶段3：BudgetAgent
await self._stream_callback.on_phase_start("BudgetAgent", "计算预算分配")
```

### 4.4 `app/services/chat_service.py`

`chat_stream()` 方法：
- 创建 `StreamCallbackHandler` 后，传递给 `SupervisorAgent`

### 4.5 `frontend/src/components/Stage.jsx`

增强 `streaming-status-panel`：

```jsx
<div className="streaming-status-panel">
  <div className="streaming-header">
    <span className="agent-name">🤖 {message.currentAgent}</span>
    <span className="skill-name">⚙️ {message.currentSkill || 'idle'}</span>
    {message.tokenUsage && (
      <span className="token-usage">
        📊 {message.tokenUsage.prompt_tokens} / {message.tokenUsage.completion_tokens} / {message.tokenUsage.total_tokens}
      </span>
    )}
  </div>
  {/* Tool calls list */}
  {message.toolCalls.map(...)}
</div>
```

### 4.6 `frontend/src/styles/global.css`

优化 `.streaming-status-panel` 样式，支持 Agent 切换动画。

---

## 5. 前端展示效果

```
┌─────────────────────────────────────────────────┐
│  🤖 PreferenceAgent    📊 Tokens: 1200 / 350 / 1550  │
│                                                 │
│  🔧 search_attractions → 正在搜索...            │
│  ✅ search_attractions → 找到 5 个景点 (230ms)  │
│                                                 │
│  [打字机输出内容...]                            │
└─────────────────────────────────────────────────┘
```

---

## 6. 改动原则

- **最小改动**：复用现有 SSE 事件机制，不新增传输层
- **事件统一**：agent_switch/skill_start/skill_end 与现有 llm_* 事件格式一致
- **前端渐进**：先确保事件能收到，再优化展示样式

---

## 7. 验收标准

1. POST 请求后，前端能在 1s 内收到 `connected` 事件
2. Agent 切换时，`streaming-status-panel` 显示新 Agent 名称
3. 工具调用时，实时显示工具名称和执行状态
4. Token 消耗实时滚动更新
5. 新 Agent 接管时，内容缓冲区正确替换
