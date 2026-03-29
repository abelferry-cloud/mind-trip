# 会话持久化设计

## 背景

当前 `SessionMemoryManager` 使用内存字典 `Dict[str, ConversationBufferMemory]` 存储会话，服务重启后数据丢失。

## 目标

将会话消息持久化到 JSONL 文件（类比 OpenClaw 的 `~/.openclaw/agents/<agentId>/sessions/<sessionId>.jsonl`），实现重启后会话恢复。

## 文件结构

```
app/memory/sessions/
  sessions.json          # 会话索引
  <session_id>.jsonl     # 每条消息一行
```

### sessions.json 格式

```json
{
  "session_id_1": {
    "created_at": "2026-03-28T10:00:00Z",
    "updated_at": "2026-03-28T15:30:00Z",
    "message_count": 10
  }
}
```

**字段维护**：`save_message()` 每次追加后同步更新 `updated_at` 和 `message_count`（读→改→写）。

### session_id.jsonl 格式（每行一条）

```jsonl
{"role": "human", "content": "我想去东京旅游", "timestamp": "2026-03-28T10:00:00Z", "user_id": "user_123"}
{"role": "ai", "content": "好的，你计划什么时候去？", "timestamp": "2026-03-28T10:00:05Z", "user_id": null}
```

**说明**：
- `user_id` 为可选项，human 消息有，ai 消息为 null
- 与 `DailyMemoryWriter` 的粒度不同：JSONL 是**每条消息一行**（更细，支持任意截断恢复）；DailyMemoryWriter 是**每对 human+ai 一组**（可读日志）

## 核心组件

### SessionPersistenceManager（新增）

| 方法 | 说明 |
|------|------|
| `save_message(session_id, role, content, user_id)` | 追加一条消息到 JSONL，同步更新 sessions.json |
| `load_session(session_id)` | 读取会话所有历史消息，返回 `List[{"role", "content", "timestamp", "user_id"}]` |
| `list_sessions()` | 读取 sessions.json 返回会话列表 |
| `delete_session(session_id)` | 删除 JSONL 文件和索引 |
| `_rebuild_index()` | 扫描所有 .jsonl 文件，重建 sessions.json（用于损坏恢复） |

**并发保护**：使用文件锁（`fcntl` on Linux / `msvcrt` on Windows）保证写入原子性。

**索引损坏恢复**：若 `sessions.json` 不存在或格式损坏，调用 `_rebuild_index()` 扫描 `sessions/` 目录下所有 `.jsonl` 文件，从文件名提取 `session_id`，从文件内容统计 `message_count` 和 `updated_at`。

### SessionMemoryManager（修改）

| 变更点 | 说明 |
|--------|------|
| `__init__` | 启动时从 JSONL 恢复所有会话到内存（调用 `_restore_all_sessions`） |
| `get_memory(session_id)` | 先检查内存，没有则从 JSONL 加载并重建 memory |
| `save_context` 后 | 同步调用 `persistence.save_message()` 写入 JSONL |

**重启恢复流程**：

```
服务启动
  → 尝试读取 sessions.json
  → 若不存在或损坏 → 调用 _rebuild_index() 重建索引
  → 对每个 session_id：
      → 创建 ConversationBufferMemory
      → 从 <session_id>.jsonl 读取所有消息
      → 构建 HumanMessage/AIMessage 对象列表
      → 通过 memory.chat_memory.messages.extend() 批量加载
```

## 与 DailyMemoryWriter 的关系

| | DailyMemoryWriter | SessionPersistence |
|---|---|---|
| 路径 | `memory/log/YYYY-MM-DD.md` | `memory/sessions/*.jsonl` |
| 格式 | Markdown，人类可读 | JSONL，机器可读 |
| 粒度 | human+ai 成对追加 | 每条消息一行 |
| 用途 | 日志审计 | 会话恢复 |

两者互补，共存。

## 实现步骤

1. 创建 `SessionPersistenceManager` 类（含文件锁和索引重建）
2. 修改 `SessionMemoryManager.__init__` 添加启动恢复逻辑 `_restore_all_sessions`
3. 修改 `SessionMemoryManager.get_memory` 添加按需从 JSONL 加载
4. 修改 `ChatService.chat` 在 `save_context` 后同步调用 `persistence.save_message()`
5. 修改 `app/api/session.py` 的 `delete_session` 同时删除 JSONL 文件

## 测试场景

1. 重启服务后，历史会话消息仍然存在
2. 新消息正确追加到 JSONL
3. 删除会话后 JSONL 文件同步删除
4. 多个会话隔离存储
5. `sessions.json` 损坏时能从 JSONL 重建索引（不丢数据）
6. 并发写入同一 session 不丢数据
