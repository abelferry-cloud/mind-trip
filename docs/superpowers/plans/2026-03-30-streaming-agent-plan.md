# 流式 Agent 执行可视化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 前端流式输出，打字机效果，实时展示 Agent/Skill/Token 消耗

**Architecture:** 复用现有 SSE 事件机制，在 StreamCallbackHandler 和 SupervisorAgent 之间建立回调链路。Supervisor 执行各阶段时发射 agent_switch/skill_start/skill_end 事件，前端负责渲染。

**Tech Stack:** FastAPI SSE + React + AsyncOpenAI streaming

---

## 文件结构

```
app/
├── services/
│   ├── stream_callback.py    # 修改：新增 on_phase_start/on_skill_start 方法
│   ├── stream_manager.py     # 修改：确认 skill_start/skill_end 方法存在
│   └── chat_service.py       # 修改：传递 stream_callback 给 Supervisor
├── agents/
│   └── supervisor.py         # 修改：plan() 接受 callback 参数，各阶段发射事件
frontend/
├── src/components/
│   └── Stage.jsx             # 修改：streaming-status-panel 展示 Agent/Skill/Token
└── src/styles/
    └── global.css            # 修改：streaming-status-panel 样式
```

---

## Task 1: 扩展 StreamCallbackHandler 和 StreamManager

**Files:**
- Modify: `app/services/stream_callback.py`
- Modify: `app/services/stream_manager.py`

- [ ] **Step 1: 修改 stream_manager.agent_switch() 支持 description 参数**

当前 `stream_manager.agent_switch(session_id, agent)` 只接受 2 个参数。需要扩展为支持 `description`：

```python
# 修改 stream_manager.py 第70-71行
async def agent_switch(self, session_id: str, agent: str, description: str = "") -> None:
    await self.emit(session_id, "agent_switch", {"agent": agent, "description": description})
```

- [ ] **Step 2: 添加 stream_manager.skill_start 和 skill_end 方法**

在 `stream_manager.py` 中添加（使用 skill_ 前缀，与设计 spec 一致）：

```python
async def skill_start(
    self, session_id: str, skill: str, tool_call_id: str
) -> None:
    await self.emit(
        session_id, "skill_start",
        {"skill": skill, "tool_call_id": tool_call_id}
    )

async def skill_end(
    self, session_id: str, skill: str, summary: Any, duration_ms: int
) -> None:
    await self.emit(
        session_id, "skill_end",
        {"skill": skill, "summary": summary, "duration_ms": duration_ms}
    )
```

- [ ] **Step 3: 添加 on_phase_start 方法到 StreamCallbackHandler**

在 `StreamCallbackHandler` 类中添加：

```python
async def on_phase_start(self, phase: str, description: str = "") -> None:
    """Agent 阶段开始，发射 agent_switch 事件。"""
    await self._stream_manager.agent_switch(self._session_id, phase, description)
```

- [ ] **Step 4: 添加 on_skill_start 和 on_skill_end 方法**

```python
async def on_skill_start(self, skill: str, tool_call_id: str) -> None:
    """Skill/Tool 开始调用，发射 skill_start 事件。"""
    await self._stream_manager.skill_start(self._session_id, skill, tool_call_id)

async def on_skill_end(
    self,
    skill: str,
    summary: Any,
    duration_ms: int,
) -> None:
    """Skill/Tool 结束，发射 skill_end 事件。"""
    await self._stream_manager.skill_end(self._session_id, skill, summary, duration_ms)
```

- [ ] **Step 5: 确认 stream_manager.emit() 支持任意事件名**

确认 `emit()` 方法存在且可接受任意 `event_name`（已确认，第30-49行）。

- [ ] **Step 6: 提交**

```bash
git add app/services/stream_callback.py app/services/stream_manager.py
git commit -m "feat(stream): add skill_start/skill_end and agent_switch with description"
```

---

## Task 2: 修改 SupervisorAgent.plan() 注入回调

**Files:**
- Modify: `app/agents/supervisor.py`

- [ ] **Step 1: 修改 plan() 方法签名，接受 stream_callback 参数**

```python
async def plan(
    self,
    user_id: str,
    session_id: str,
    message: str,
    stream_callback: Optional[Any] = None,  # 新增
) -> Dict[str, Any]:
```

- [ ] **Step 2: 在各阶段执行前发射 agent_switch 事件**

在 `plan()` 方法内，每个 `await` 调用前添加：

```python
# 解析意图后
if stream_callback:
    await stream_callback.on_phase_start("PreferenceAgent", "解析用户偏好")

# PreferenceAgent 执行
pref_result = await trace("PreferenceAgent",
    self.pref_agent.parse_and_update(user_id, message))
```

```python
# 并行搜索前
if stream_callback:
    await stream_callback.on_phase_start("TravelPlanner", "搜索景点、餐厅、酒店")

search_result, budget_result = await asyncio.gather(
    trace("TravelPlanner Agent (search)", ...),
    trace("Budget Agent", ...)
)
```

```python
# 路线规划前
if stream_callback:
    await stream_callback.on_phase_start("RouteAgent", "规划每日路线")
```

```python
# 预算验证前
if stream_callback:
    await stream_callback.on_phase_start("BudgetAgent", "验证预算")
```

- [ ] **Step 3: 修改 trace() 包装器，接受 stream_callback 参数**

找到 `supervisor.py` 第92-104行的 `trace()` 函数，将其扩展为接受 `stream_callback`：

```python
async def trace(agent_name: str, coro, stream_callback=None):
    """包装器用于计时 Agent 调用，并可选地发射 agent_switch 事件。"""
    agent_trace["agents"].append(agent_name)
    agent_trace["invocation_order"].append(len(agent_trace["agents"]))
    t = time.time()
    if stream_callback:
        await stream_callback.on_phase_start(agent_name, "")
    try:
        result = await coro
        agent_trace["durations_ms"].append(int((time.time() - t) * 1000))
        return result
    except Exception as e:
        agent_trace["durations_ms"].append(int((time.time() - t) * 1000))
        agent_trace["errors"].append({"agent": agent_name, "error": str(e)})
        raise
```

- [ ] **Step 4: 找到所有调用 trace() 的地方**

确认 `supervisor.py` 中所有 `await trace(...)` 调用，在 `plan()` 方法内传递 `stream_callback` 参数（当前有4处，见下方 Step 5）。

- [ ] **Step 5: 传递 stream_callback 给所有 trace() 调用**

修改 `plan()` 方法内的 4 处 `await trace(...)` 调用，传递 `stream_callback`：

```python
# 第1处: PreferenceAgent
pref_result = await trace("PreferenceAgent",
    self.pref_agent.parse_and_update(user_id, message), stream_callback)

# 第2处: TravelPlanner search
search_result, budget_result = await asyncio.gather(
    trace("TravelPlanner Agent (search)", self.travel_agent.search_all(...), stream_callback),
    trace("Budget Agent", self.budget_agent.calculate(...), stream_callback)
)

# 第3处: TravelPlanner route
route_result = await trace("TravelPlanner Agent (route)",
    self.travel_agent.plan_routes(attractions, {...}), stream_callback)

# 第4处: BudgetAgent validation
budget_check = await trace("BudgetAgent (validation)",
    self.budget_agent.check_plan(budget, plan_summary), stream_callback)
```

- [ ] **Step 4: 提交**

```bash
git add app/agents/supervisor.py
git commit -m "feat(supervisor): emit agent_switch events via stream_callback"
```

---

## Task 3: 修改 chat_service.py 使用 Supervisor 路由

**Files:**
- Modify: `app/services/chat_service.py`
- Import: `app.agents.supervisor.PlanningAgent`

**关键架构决策**：当前 `chat_stream()` 直接调用 `ModelRouter.call_with_tools()`，不经过 Supervisor。为了实现 Agent 级别的流式可视化，需要改为通过 `SupervisorAgent.plan()` 路由。

- [ ] **Step 1: 分析 chat_stream() 当前实现**

查看 `app/services/chat_service.py` 第117-183行 `chat_stream()` 方法。当前它：
1. 加载 system prompt
2. 加载 session memory
3. 调用 `ModelRouter.call_with_tools()`
4. 不经过任何 Agent 协调

- [ ] **Step 2: 添加 PlanningAgent 到 chat_stream()**

在 `chat_stream()` 方法中添加 `PlanningAgent` 调用：

```python
from app.agents.supervisor import PlanningAgent

# 在 try 块内（大约第163行）
try:
    # 原有: answer = await self._router.call_with_tools(...)
    # 改为: 使用 Supervisor 路由
    supervisor = PlanningAgent()
    result = await supervisor.plan(
        user_id=user_id,
        session_id=session_id,
        message=message,
        stream_callback=callback,  # 传递流式回调
    )
    answer = result.get("answer", "")  # Supervisor 返回包含 answer 的 dict
```

注意：`SupervisorAgent.plan()` 返回的是包含 `answer`、`daily_routes`、`budget_summary` 等字段的完整规划结果，不是简单的字符串。

- [ ] **Step 3: 处理 Supervisor 返回值**

Supervisor.plan() 返回结构：
```python
{
    "plan_id": "...",
    "city": "...",
    "answer": "已为您规划北京3天行程...",
    "daily_routes": [...],
    "budget_summary": {...},
    # ...
}
```

需要从中提取 `answer` 字段作为最终回复：

```python
answer = result.get("answer", "")
```

- [ ] **Step 4: 确认 PlanningAgent 的 plan() 接受 stream_callback**

修改 `app/agents/supervisor.py` 中 `plan()` 签名（见 Task 2 Step 1）。

- [ ] **Step 5: 提交**

```bash
git add app/services/chat_service.py
git commit -m "feat(chat_service): route through Supervisor for agent streaming"
```

---

## Task 4: 前端 Stage.jsx 增强展示

**Files:**
- Modify: `frontend/src/components/Stage.jsx`

- [ ] **Step 1: 添加 currentAgent 和 currentSkill 状态到消息对象**

在 `createStreamingMessage()` 返回的对象中添加：

```javascript
{
  // ... 现有字段
  currentAgent: 'PlanningAgent',  // 当前执行中的 Agent
  currentSkill: null,              // 当前执行中的 Skill/Tool
  phaseDescription: '',             // 阶段描述
}
```

- [ ] **Step 2: 添加 agent_switch 事件处理**

在 `startStreaming()` 函数的 EventSource 处理中添加：

```javascript
es.addEventListener('agent_switch', (e) => {
  const { agent, description } = JSON.parse(e.data)
  const updated = messagesRef.current.map(msg =>
    msg.id === messageId
      ? { ...msg, currentAgent: agent, phaseDescription: description || '', contentBuffer: '', content: '' }
      : msg
  )
  onUpdateMessage(sessionId, updated)
})
```

注意：`contentBuffer: '', content: ''` 实现"新 Agent 接管时清空输出"。

- [ ] **Step 3: 添加 skill_start 事件处理（Supervisor 规划阶段发出）**

```javascript
es.addEventListener('skill_start', (e) => {
  const { skill, tool_call_id } = JSON.parse(e.data)
  const updated = messagesRef.current.map(msg =>
    msg.id === messageId
      ? { ...msg, currentSkill: skill }
      : msg
  )
  onUpdateMessage(sessionId, updated)
})
```

注意：ToolCallingService 发出的是 `tool_start`（已存在），Supervisor 的规划阶段发出的是 `skill_start`。两者都更新 `currentSkill` 字段，实现统一展示。

- [ ] **Step 4: 修改 streaming-status-panel 渲染**

找到现有的 `streaming-status-panel` div（约第417行），修改为：

```jsx
<div className="streaming-status-panel">
  <div className="streaming-header">
    <span className="agent-name">🤖 {message.currentAgent || message.agent}</span>
    {message.currentSkill && (
      <span className="skill-name">⚙️ {message.currentSkill}</span>
    )}
    {message.phaseDescription && (
      <span className="phase-description">{message.phaseDescription}</span>
    )}
    {message.model && <span className="model-name">via {message.model}</span>}
  </div>

  {message.tokenUsage && (
    <div className="token-usage">
      📊 Prompt: {message.tokenUsage.prompt_tokens} |
      Completion: {message.tokenUsage.completion_tokens} |
      Total: {message.tokenUsage.total_tokens}
      {message.tokenUsage.cost_usd && ` ($${message.tokenUsage.cost_usd})`}
    </div>
  )}
  {/* 保留 toolCalls 展示 */}
</div>
```

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/Stage.jsx
git commit -m "feat(frontend): display agent/skill in streaming panel"
```

---

## Task 5: 样式优化

**Files:**
- Modify: `frontend/src/styles/global.css`

- [ ] **Step 1: 查找现有 streaming-status-panel 样式**

在 `global.css` 第207行附近找到 `.streaming-status-panel`。

- [ ] **Step 2: 添加 Agent/Skill 展示样式**

```css
.streaming-header {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.agent-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--accent-primary);
}

.skill-name {
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  padding: 2px 8px;
  border-radius: 4px;
}

.phase-description {
  font-size: 12px;
  color: var(--text-muted);
  font-style: italic;
}

.token-usage {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
}
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/styles/global.css
git commit -m "feat(frontend): style agent/skill display in streaming panel"
```

---

## Task 6: 端到端测试验证

- [ ] **Step 1: 启动后端**

```bash
cd D:\pychram-workspace\smartJournal
python -m app.main
```

- [ ] **Step 2: 启动前端**

```bash
cd frontend
npm run dev
```

- [ ] **Step 3: 测试场景**

1. 打开浏览器访问 http://localhost:5173
2. 输入旅行需求，如"去北京3天，预算5000元"
3. 观察 streaming-status-panel：
   - 是否显示 "🤖 PreferenceAgent"
   - 是否有 "⚙️ search_attractions" 技能展示
   - Token 消耗是否实时更新
   - Agent 切换时内容是否被清空
4. 检查浏览器控制台是否有事件日志

---

## 验收标准

1. ✅ POST 请求后，前端能在 1s 内收到 `connected` 事件
2. ✅ Agent 切换时，`streaming-status-panel` 显示新 Agent 名称
3. ✅ 工具调用时，实时显示工具名称和执行状态
4. ✅ Token 消耗实时滚动更新
5. ✅ 新 Agent 接管时，内容缓冲区正确替换
