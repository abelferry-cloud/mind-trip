# Chat API 响应格式精简设计

**日期：** 2026-03-28
**状态：** 已批准

## 1. 目标

清理 Chat API 响应中的调试字段，精简响应格式，同时为未来多智能体推理链预留扩展。

## 2. 现状

当前 `ChatResponse` 包含调试字段，不适合作为正式 API 响应：

```python
class ChatResponse(BaseModel):
    answer: str
    system_prompt: str       # 过大，仅调试用
    model_used: str          # 调试用
    workspace_loaded_at: str # 调试用
    history_count: int       # 调试用
```

## 3. 方案

### 3.1 新响应结构

```python
class ChatResponse(BaseModel):
    answer: str                    # Markdown 格式的回复文本
    metadata: dict                 # 元数据
    reasoning: Optional[dict]      # Agent reasoning trace（预留，未来填充）
```

**metadata 字段定义：**
```python
{
    "model": "deepseek",          # 实际使用的模型
    "timestamp": "2026-03-28T10:30:00Z"
}
```

**reasoning 字段（当前返回 null，未来支持多智能体时填充）：**
```python
{
    "agents": [
        {"name": "PlanningAgent", "status": "completed", "output": "..."},
        {"name": "AttractionsAgent", "status": "completed", "output": "..."}
    ],
    "steps": [
        {"agent": "PlanningAgent", "input": "...", "output": "..."}
    ]
}
```

### 3.2 移除字段

| 字段 | 移除原因 |
|------|----------|
| `system_prompt` | 整个 workspace 内容过大（>10KB），仅调试用 |
| `workspace_loaded_at` | 调试时间戳，对前端无意义 |
| `history_count` | 调试用消息计数 |
| `model_used` | 合并至 `metadata.model` |

### 3.3 后端改动

**文件：`app/api/chat.py`**
- 修改 `ChatResponse` 模型，移除 `system_prompt`、`workspace_loaded_at`、`history_count`、`model_used`
- 新增 `metadata: dict` 和 `reasoning: Optional[dict]`
- 调整 `return ChatResponse(...)` 的字段映射

**文件：`app/services/chat_service.py`**
- 修改 `chat()` 方法返回值，新增 `metadata` 字段
- `reasoning` 当前返回 `None`，作为预留扩展点

### 3.4 前端适配

**文件：`frontend/src/components/Stage.jsx`**
- `data.system_prompt` → 移除
- `data.model_used` → 改为 `data.metadata.model`
- `data.workspace_loaded_at` → 移除
- `data.history_count` → 移除

## 4. 向后兼容

- 移除的字段均为调试用途，不影响业务功能
- 前端需同步更新，否则会读取 undefined 值

## 5. 未来扩展

当多智能体协作实现后，`reasoning` 字段将填充真实的 agent 执行链路：

```python
{
    "reasoning": {
        "agents": [
            {"name": "PlanningAgent", "status": "completed"},
            {"name": "AttractionsAgent", "status": "completed"},
            {"name": "RouteAgent", "status": "completed"}
        ],
        "steps": [
            {
                "agent": "PlanningAgent",
                "thought": "解析用户意图：目的地重庆，3天，预算5000",
                "output": "生成初步规划框架"
            }
        ]
    }
}
```
