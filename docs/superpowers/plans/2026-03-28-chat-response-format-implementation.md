# Chat API 响应格式精简实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 精简 Chat API 响应格式，移除调试字段，新增 metadata 和预留 reasoning 字段。

**Architecture:** 修改 `ChatResponse` Pydantic 模型和 `chat_service.py` 的返回结构，前端同步适配。

**Tech Stack:** FastAPI, Pydantic, React

---

## 文件结构

| 文件 | 改动 |
|------|------|
| `app/api/chat.py` | 修改 `ChatResponse` 模型，移除旧字段，新增 `metadata` 和 `reasoning` |
| `app/services/chat_service.py` | 修改 `chat()` 返回值，新增 `metadata` 字段 |
| `frontend/src/components/Stage.jsx` | 适配新的响应字段，移除对旧字段的引用 |

---

## 实现步骤

### Task 1: 修改后端 ChatResponse 模型

**Files:**
- Modify: `app/api/chat.py:28-33`

- [ ] **Step 1: 修改 ChatResponse 模型**

```python
class ChatResponse(BaseModel):
    answer: str
    metadata: dict
    reasoning: Optional[dict] = None
```

- [ ] **Step 2: 修改 return 语句**

原代码（第76-81行）:
```python
return ChatResponse(
    answer=result["answer"],
    system_prompt=result["system_prompt"],
    model_used=result["model_used"],
    workspace_loaded_at=result["workspace_loaded_at"],
    history_count=result.get("history_count", 0),
)
```

修改为:
```python
return ChatResponse(
    answer=result["answer"],
    metadata=result.get("metadata", {}),
    reasoning=result.get("reasoning"),
)
```

- [ ] **Step 3: 修改 TimeoutError 返回（第54-62行）**

原代码:
```python
return JSONResponse(
    status_code=200,
    content={
        "answer": "请求超时，请稍后重试",
        "system_prompt": "",
        "model_used": "",
        "workspace_loaded_at": "",
        "history_count": 0,
    }
)
```

修改为:
```python
return JSONResponse(
    status_code=200,
    content={
        "answer": "请求超时，请稍后重试",
        "metadata": {"model": "", "timestamp": ""},
        "reasoning": None,
    }
)
```

- [ ] **Step 4: 修改 Exception 返回（第65-73行）**

原代码:
```python
return JSONResponse(
    status_code=200,
    content={
        "answer": f"出错了：{str(e)}",
        "system_prompt": "",
        "model_used": "",
        "workspace_loaded_at": "",
        "history_count": 0,
    }
)
```

修改为:
```python
return JSONResponse(
    status_code=200,
    content={
        "answer": f"出错了：{str(e)}",
        "metadata": {"model": "", "timestamp": ""},
        "reasoning": None,
    }
)
```

- [ ] **Step 5: 提交**
```bash
git add app/api/chat.py && git commit -m "refactor(chat): simplify ChatResponse format"
```

---

### Task 2: 修改 chat_service 返回值

**Files:**
- Modify: `app/services/chat_service.py:85-91`

- [ ] **Step 1: 添加 datetime import 并修改返回结构**

在 `app/services/chat_service.py` 第10行附近添加 import：
```python
from datetime import datetime, timezone
```

原代码:
```python
return {
    "answer": answer,
    "system_prompt": system_prompt,
    "model_used": model_used,
    "workspace_loaded_at": workspace_loaded_at,
    "history_count": history_count,
}
```

修改为:
```python
return {
    "answer": answer,
    "metadata": {
        "model": model_used,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    },
    "reasoning": None,  # 预留扩展
}
```

- [ ] **Step 2: 提交**
```bash
git add app/services/chat_service.py && git commit -m "refactor(chat_service): return metadata instead of debug fields"
```

---

### Task 3: 前端适配

**Files:**
- Modify: `frontend/src/components/Stage.jsx:56-66`

- [ ] **Step 1: 适配 metadata 字段**

原代码（第56-66行）:
```javascript
const data = await response.json()

const assistantMessage = {
  id: (Date.now() + 1).toString(),
  role: 'assistant',
  content: data.answer || '抱歉，发生了错误。',
  systemPrompt: data.system_prompt,
  modelUsed: data.model_used,
  timestamp: new Date().toISOString(),
  thoughts: generateMockThoughts(data.answer)
}
```

修改为:
```javascript
const data = await response.json()

const assistantMessage = {
  id: (Date.now() + 1).toString(),
  role: 'assistant',
  content: data.answer || '抱歉，发生了错误。',
  modelUsed: data.metadata?.model,
  timestamp: data.metadata?.timestamp || new Date().toISOString(),
  thoughts: generateMockThoughts(data.answer)
}
```

- [ ] **Step 2: 提交**
```bash
git add frontend/src/components/Stage.jsx && git commit -m "refactor(frontend): adapt to new ChatResponse format"
```

---

## 验证步骤

- [ ] 启动后端: `python -m app.main`
- [ ] 测试 API: `curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{"user_id":"test","session_id":"s1","message":"重庆三日游推荐"}'`
- [ ] 验证响应包含 `answer`, `metadata` 字段，无 `system_prompt` 等调试字段
- [ ] 启动前端，发送消息验证聊天功能正常
