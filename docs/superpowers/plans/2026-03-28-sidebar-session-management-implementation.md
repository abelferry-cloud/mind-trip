# Sidebar Session Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现侧边栏会话点击加载历史消息功能

**Architecture:** 在 App.jsx 添加消息加载逻辑，Stage.jsx 复用现有渲染逻辑显示历史消息。会话名称继续使用 localStorage 本地存储。

**Tech Stack:** React, localStorage, Fetch API

---

## File Structure

- Modify: `frontend/src/App.jsx` — 添加消息加载状态和切换逻辑
- Modify: `frontend/src/components/Stage.jsx` — 接收 historyMessages prop 并渲染

---

## Implementation Tasks

### Task 1: App.jsx 添加消息加载状态

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: 添加 loadingMessages 状态**

在 `frontend/src/App.jsx` 第 10 行附近，找到:
```javascript
const [currentSessionId, setCurrentSessionId] = useState(null)
```

在这行后面添加:
```javascript
const [loadingMessages, setLoadingMessages] = useState(false)
```

- [ ] **Step 2: 添加 historyMessages 缓存状态**

在同一位置添加:
```javascript
const [historyMessages, setHistoryMessages] = useState({})
```

- [ ] **Step 3: 修改 handleSelectSession 函数**

找到现有的 `handleSelectSession` 函数（约第 82-84 行），替换为:
```javascript
const handleSelectSession = async (sessionId) => {
  setCurrentSessionId(sessionId)

  // 懒加载：如果没有消息记录，则请求历史
  if (!historyMessages[sessionId]) {
    setLoadingMessages(true)
    try {
      const response = await fetch(`/api/sessions/${sessionId}/messages`)
      if (!response.ok) throw new Error('Failed to fetch messages')
      const data = await response.json()
      setHistoryMessages(prev => ({
        ...prev,
        [sessionId]: data.messages || []
      }))
    } catch (error) {
      console.error('Failed to load messages:', error)
      setHistoryMessages(prev => ({
        ...prev,
        [sessionId]: []
      }))
    } finally {
      setLoadingMessages(false)
    }
  }
}
```

- [ ] **Step 4: 将 historyMessages 传递给 Stage 组件**

找到 Stage 组件调用（约第 192-203 行），添加 prop:
```javascript
<Stage
  style={{ flex: 1 }}
  session={currentSession}
  messages={historyMessages[currentSession?.id] || []}
  loadingMessages={loadingMessages}
  onUpdateMessage={handleUpdateMessage}
  onUpdateSessionTitle={handleUpdateSessionTitle}
  inspectorFile={inspectorFile}
  onInspectorFileChange={setInspectorFile}
  inputHeight={inputHeight}
  onInputHeightChange={setInputHeight}
  onResizeStart={(e) => handleResizeStart(e, 'input')}
  resizing={resizing === 'input'}
/>
```

- [ ] **Step 5: 提交代码**

```bash
git add frontend/src/App.jsx
git commit -m "feat(frontend): add session message loading on select"
```

---

### Task 2: Stage.jsx 支持历史消息渲染

**Files:**
- Modify: `frontend/src/components/Stage.jsx`

- [ ] **Step 1: 修改 Stage 组件接收 messages 和 loadingMessages props**

找到 Stage 组件函数签名（约第 6-16 行）:
```javascript
const Stage = ({
  session,
  onUpdateMessage,
  ...
})
```

替换为:
```javascript
const Stage = ({
  session,
  messages,
  loadingMessages,
  onUpdateMessage,
  ...
})
```

- [ ] **Step 2: 用 props.messages 替换 session.messages**

找到消息渲染逻辑（约第 141-195 行）:
```javascript
{session.messages.length === 0 ? (
  ...
) : (
  session.messages.map(message => (
```

替换为:
```javascript
const displayMessages = messages.length > 0 ? messages : session.messages

{displayMessages.length === 0 ? (
  ...
) : (
  displayMessages.map(message => (
```

- [ ] **Step 3: 添加历史消息加载状态显示**

在 `messages-container` 开头（约第 141 行附近），在 `{session.messages.length === 0 ? (` 之前添加:
```javascript
{loadingMessages && (
  <div className="loading-history">
    <div className="loading-spinner small"></div>
    <span>加载历史消息...</span>
  </div>
)}
```

- [ ] **Step 4: 添加加载样式**

打开 `frontend/src/styles/App.css`，在文件末尾添加:
```css
.loading-history {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  color: var(--text-secondary);
}

.loading-spinner.small {
  width: 16px;
  height: 16px;
}
```

- [ ] **Step 5: 提交代码**

```bash
git add frontend/src/components/Stage.jsx frontend/src/styles/App.css
git commit -m "feat(frontend): render historical messages in Stage"
```

---

### Task 3: 测试完整流程

- [ ] **Step 1: 启动后端服务**

```bash
cd D:\pychram-workspace\smartJournal
python -m app.main
```

- [ ] **Step 2: 启动前端服务**

```bash
cd D:\pychram-workspace\smartJournal\frontend
npm run dev
```

- [ ] **Step 3: 验证功能**

1. 打开 http://localhost:5173
2. 确认会话列表正常显示
3. 点击一个已有会话，确认"加载历史消息..."提示出现
4. 确认历史消息正确渲染
5. 切换会话再切回，确认使用缓存不重复请求
6. 测试手动重命名会话
7. 测试删除会话

---

## Verification Commands

```bash
# 后端健康检查
curl http://localhost:8000/api/sessions

# 获取单个会话消息
curl http://localhost:8000/api/sessions/test_session_001/messages
```
