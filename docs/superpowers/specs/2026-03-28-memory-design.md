# 记忆系统设计方案

## 1. 概述

**目标：** 在现有 `ChatService` 基础上，集成 OpenClaw 风格的双层记忆 + LangChain LCEL 管道，实现真正的智能对话记忆功能。

**设计原则：**
- 参考 OpenClaw 的双层记忆架构（Layer 2 Workspace + Layer 4 对话历史）
- 使用 LangChain LCEL 管道组合各组件
- 暂不包含工具调用，聚焦记忆功能

---

## 2. 记忆架构

### 2.1 双层记忆

| 层级 | 类型 | 存储 | 用途 |
|------|------|------|------|
| Layer 2 (Workspace) | System Prompt | `app/workspace/*.md` | 角色定位、能力边界、安全规则 |
| Layer 4 (对话历史) | 短期对话 | `ConversationBufferMemory` (内存) | 当前会话上下文 |
| Layer 4 (每日日志) | 每日记录 | `workspace/memory/YYYY-MM-DD.md` | 跨会话持久化对话 |
| Layer 2 (长期) | 结构化记忆 | SQLite `preferences/trip_history` | 用户偏好、旅行历史 |

### 2.2 数据流

```
用户消息
    ↓
WorkspacePromptLoader.invoke()  →  system_prompt (Layer 2)
ConversationBufferMemory.get_messages() →  history (Layer 4)
    ↓
组装: system_prompt + history + user_message
    ↓
ChatModel → response
    ↓
保存:
  - ConversationBufferMemory.save_context(input, output)  → 短期记忆
  - workspace/memory/YYYY-MM-DD.md 追加写入  → 每日日志
  - SQLite (via MemoryService)  → 长期偏好/历史
```

---

## 3. 组件设计

### 3.1 WorkspacePromptLoader

**已有**：`app/graph/sys_prompt_builder.py` 中的 `WorkspacePromptLoader`

**职责：** 每次调用时从 `app/workspace/*.md` 动态加载 system prompt

**输出：** `{"system_prompt": str, "workspace_loaded_at": str}`

### 3.2 ConversationBufferMemory

**来源：** LangChain 内置 `langchain.memory.ConversationBufferMemory`

**职责：**
- 存储当前会话的对话历史（HumanMessage / AIMessage）
- `save_context(input, output)` — 保存一对对话
- `get_history()` — 获取可格式化的历史消息

### 3.3 DailyMemoryWriter

**新增组件**

**职责：**
- 每次对话后，将对话追加写入 `workspace/memory/YYYY-MM-DD.md`
- 格式：`[HH:MM:SS]\nHuman: ...\nAI: ...\n`

**文件路径：** `app/workspace/memory/YYYY-MM-DD.md`

### 3.4 SessionMemoryManager

**新增组件**

**职责：**
- 管理 `session_id` → `ConversationBufferMemory` 的映射
- 按 session_id 隔离对话历史
- 定时清理过期会话（可选）

### 3.5 ChatChain（LCEL 管道）

**核心管道：**

```python
from langchain_core.runnables import RunnableLambda
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage

# 伪代码结构
class ChatChain:
    def __init__(self, session_id: str):
        self.prompt_loader = get_supervisor_loader(mode="main")
        self.memory = ConversationBufferMemory(
            return_messages=True,
            output_key="answer",
            input_key="input"
        )
        self.model = get_model_router()

    async def chat(self, user_id: str, session_id: str, message: str) -> dict:
        # 1. 动态加载 system prompt
        prompt_result = self.prompt_loader.invoke({})
        system_prompt = prompt_result["system_prompt"]

        # 2. 获取对话历史
        history_messages = self.memory.get_history()

        # 3. 组装完整消息
        full_prompt = f"{system_prompt}\n\n## 对话历史\n{format_history(history_messages)}\n\n## 当前消息\n{message}"

        # 4. 调用模型
        response = await self.model.call(full_prompt)

        # 5. 保存到记忆
        self.memory.save_context({"input": message}, {"output": response})
        self._append_daily_log(user_id, session_id, message, response)

        return {
            "answer": response,
            "system_prompt": system_prompt,
            "workspace_loaded_at": prompt_result["workspace_loaded_at"],
        }
```

---

## 4. 数据存储

### 4.1 每日日志文件

**路径：** `app/workspace/memory/YYYY-MM-DD.md`

**格式：**
```markdown
# 2026-03-28

## Session: abc123

[20:45:33]
Human: 我想下周去成都玩3天
AI: 太棒了！成都是一个美食之都，您对辣的食物接受程度如何？

[20:46:12]
Human: 我不太能吃辣
AI: 了解！那我会在规划时避开川菜为主的餐厅，为您推荐一些清淡的粤菜或其他菜系。

## Session: def456

[21:00:00]
Human: ...
AI: ...
```

### 4.2 SQLite 长期记忆

**已有表结构**（`app/memory/long_term.py`）：
- `preferences` — 用户偏好（健康、消费风格等）
- `trip_history` — 历史旅行记录
- `feedback` — 用户反馈

**写入时机：**
- `PreferenceAgent` 解析到偏好时 → 写入 `preferences`
- 用户完成旅行规划后 → 写入 `trip_history`

### 4.3 内存对话历史

**存储：** `ConversationBufferMemory`（按 `session_id` 隔离）

**生命周期：** 会话期间持在内存，会话结束后可选择清理

---

## 5. 安全与隔离

### 5.1 会话隔离

- 每个 `session_id` 有独立的 `ConversationBufferMemory` 实例
- 不同用户的对话历史不会混淆

### 5.2 敏感信息

- MEMORY.md（长期记忆）包含用户敏感偏好，仅通过 `mode="main"` 加载
- 每日日志文件按 `session_id` 记录，同一会话内的对话不会泄露给其他会话

---

## 6. 实现步骤

### Phase 1: 基础记忆（本次实现）
1. 创建 `DailyMemoryWriter` — 每日日志追加写入
2. 创建 `SessionMemoryManager` — 管理会话级 `ConversationBufferMemory`
3. 修改 `ChatService` — 集成记忆读写，每次对话保存到内存
4. 测试记忆持久化 — 验证 `session_id` 隔离和历史加载

### Phase 2: 长期记忆整合（后续）
1. 在 `ChatService` 中调用 `MemoryService` 读取偏好/历史
2. 将偏好信息注入 system prompt context
3. 对话结束后保存到 `trip_history`

---

## 7. 文件变更

### 新增文件
- `app/memory/daily_writer.py` — DailyMemoryWriter
- `app/memory/session_manager.py` — SessionMemoryManager

### 修改文件
- `app/services/chat_service.py` — 集成记忆功能
- `app/api/chat.py` — 更新响应格式

### 不变更
- `app/graph/sys_prompt_builder.py` — 已完成
- `app/memory/long_term.py` — 已有表结构
- `app/memory/short_term.py` — 保留（其他模块可能使用）

---

## 8. 测试验证

1. **对话记忆测试** — 连续2次对话，验证第2次能引用第1次内容
2. **会话隔离测试** — 不同 `session_id` 的历史互不影响
3. **每日日志测试** — 重启服务后，`workspace/memory/YYYY-MM-DD.md` 存在且可追加
4. **动态加载测试** — 修改 `workspace/SOUL.md` 后，新对话立即生效

---

## 9. 关键设计决策记录

| 决策 | 选项 | 原因 |
|------|------|------|
| 记忆用途 | C (两者都要) | 旅行偏好 + 对话上下文 |
| 对话记忆存储 | A (文本 .md) | 简单、OpenClaw 风格、直接可读 |
| 加载方式 | C (全部加载) | 让模型自己决定引用哪些 |
| 会话隔离 | C (仅 main session) | 项目无群组需求，简化实现 |
| 历史加载时机 | B (LangChain ConversationBufferMemory) | LangChain 内置组件 |
| 架构集成 | C (LangChain LCEL 管道) | 扩展性强，符合 LangChain 设计哲学 |
