# 侧边栏会话管理功能设计

## 概述

为 Smart Travel Journal 的侧边栏添加完整的会话管理功能：加载会话列表、显示会话名称（支持手动修改）、点击会话加载历史对话。

## 现状分析

**已有能力：**
- `GET /api/sessions` 已在 App.jsx 中调用
- 会话列表渲染已实现
- 新建会话功能已实现
- 会话本地重命名已实现（仅保存在 localStorage）
- 首条用户消息自动设为会话标题已实现

**缺失能力：**
- 点击会话时未加载历史消息
- 旧会话的消息未从后端获取

## 设计方案

### 1. 数据加载流程

```
App 组件加载时:
  → 调用 GET /api/sessions
  → 合并本地存储的会话名称
  → 渲染会话列表

点击会话时:
  → 如果 messages 为空
    → 显示加载状态
    → 调用 GET /api/sessions/{session_id}/messages
    → 保存到 session state
    → 渲染历史消息
  → 如果 messages 非空
    → 直接切换显示（不重复请求）
```

### 2. 会话名称管理

| 操作 | 存储位置 | 说明 |
|------|----------|------|
| 新建会话 | localStorage | 默认为"新会话" |
| 首条用户消息 | localStorage | Stage.jsx 设置 |
| 手动修改 | localStorage | Sidebar 内联编辑 |
| 旧会话加载 | localStorage | 从 sessionStorage 读取 |

**Key:** `session_titles`, **Value:** `{ [session_id]: title }`

### 3. 组件职责划分

| 组件 | 职责 |
|------|------|
| `App.jsx` | 会话列表状态管理、API 调用、切换逻辑 |
| `Sidebar.jsx` | 仅负责 UI 展示和编辑交互 |
| `Stage.jsx` | 消息渲染、发送消息、首条消息设标题 |

### 4. API 接口

**GET /api/sessions/{session_id}/messages**

Response:
```json
{
  "session_id": "test_session_001",
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "我想去东京旅行",
      "timestamp": "2026-03-28T10:00:00Z"
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "好的，我来为你规划东京之旅...",
      "timestamp": "2026-03-28T10:00:01Z"
    }
  ]
}
```

### 5. 状态结构

```javascript
// App.jsx sessions state
{
  id: string,           // session_id
  session_id: string,
  title: string,        // 显示名称，从 localStorage 读取
  history_count: number,
  has_memory: boolean,
  messages: Array<{id, role, content, timestamp}>  // 懒加载
}
```

### 6. 加载状态

在 `App.jsx` 添加:
- `loadingMessages: boolean` - 加载历史消息时显示
- `selectedSessionMessages: object` - 当前会话的历史消息缓存

### 7. UI 变更

**Sidebar 会话项：**
- 显示标题（支持点击编辑）
- 显示 `history_count` 和 `has_memory` badge
- 编辑/删除操作按钮

**Stage 消息区：**
- 加载历史消息时显示 loading spinner
- 历史消息正常渲染
- 之后可以继续发送新消息

## 实现步骤

1. App.jsx: 修改 `handleSelectSession` 添加消息加载逻辑
2. App.jsx: 添加 `loadingMessages` 状态和历史消息缓存
3. App.jsx: Stage 组件传递 `loadingMessages` 和历史消息
4. Stage.jsx: 接收并渲染历史消息（复用现有消息渲染逻辑）
5. 测试完整流程

## 错误处理

- 加载消息失败：显示错误提示，保持在当前会话
- 网络断开：使用缓存的 messages（如有）
