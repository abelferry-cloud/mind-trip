# 前端对话页面设计文档

> 日期：2026-03-27
> 目标：为 smartJournal 项目编写 React 前端对话页面，调用 POST /api/chat 接口

---

## 1. 视觉风格

- **主题**：浅色主题，白色/浅灰背景，清新旅行感配色
- **强调色**：蓝色（#3B82F6）用于按钮和交互元素
- **字体**：系统默认无衬线字体（Inter / -apple-system / sans-serif）

## 2. 页面布局

```
┌──────────────────────────────────────┐
│           顶部导航栏                  │
│  "SmartJourney 智能出行规划"           │
├──────────────────────────────────────┤
│                                      │
│           对话消息区域                │
│    （用户消息右侧，AI消息左侧）          │
│                                      │
│    [user] 我想去北京玩3天...           │
│                          [发送按钮]   │
│                                      │
│    [ai] 为您规划了北京3天行程...       │
│         plan_id: xxx                 │
│         health_alerts: [...]         │
│         preference_compliance: [...] │
│                                      │
├──────────────────────────────────────┤
│           底部输入框                  │
│  [请输入您的出行需求...        ] [发送] │
└──────────────────────────────────────┘
```

- **消息气泡**：
  - 用户消息：蓝色背景（#3B82F6），白色文字，右对齐
  - AI 消息：浅灰背景（#F3F4F6），深灰文字，左对齐
- **输入框**：固定在底部，圆角边框，placeholder 提示文字
- **发送按钮**：蓝色圆形/矩形按钮，hover 时加深

## 3. 交互流程

### 3.1 发送消息

1. 用户在输入框输入文字（如"我想去北京玩3天，请帮我规划行程"）
2. 点击发送按钮或按 Enter 键
3. 消息立即添加到对话列表（用户气泡）
4. 输入框清空
5. 显示加载状态："正在规划您的行程，请稍候..."

### 3.2 收到响应

1. 隐藏加载状态
2. 添加 AI 消息气泡，显示：
   - `answer` 字段（行程规划确认文字）
   - `plan_id` 字段（小字显示）
   - `health_alerts` 数组（每条alert单独一行，黄色/橙色高亮背景）
   - `preference_compliance` 数组（每条单独一行，绿色高亮背景）
   - `agent_trace` 折叠展示（可选展开，显示 agent 调用链）
3. 如果请求超时：显示超时提示

### 3.3 错误处理

- 网络错误：显示红色错误气泡 "网络连接失败，请检查网络后重试"
- API 返回错误：显示错误详情

## 4. 数据结构

### 请求

```json
POST /api/chat
{
  "user_id": "test_user_001",
  "session_id": "test_session_001",
  "message": "我想去北京玩 3 天，请帮我规划行程"
}
```

### 响应

```json
{
  "answer": "为您规划了北京3天行程，祝您旅途愉快！",
  "plan_id": "plan_xxx",
  "agent_trace": {
    "agents": [...],
    "invocation_order": [...],
    "durations_ms": [...],
    "errors": []
  },
  "health_alerts": ["您的行程包含较多步行，建议随身携带日常药物"],
  "preference_compliance": ["已为您排除硬座选项，全程优先选择卧铺/座位"]
}
```

## 5. 技术方案

- **框架**：React 18 + Vite
- **HTTP 客户端**：原生 fetch 或 axios
- **样式**：CSS Modules 或 styled-components（保持轻量）
- **状态管理**：React useState + useRef（无需 Redux）
- **session_id**：前端生成 UUID，随会话持久化（刷新不重置）
- **user_id**：固定 "test_user_001"（演示用）

## 6. 组件清单

| 组件 | 职责 |
|------|------|
| `App` | 根组件，管理全局状态 |
| `ChatHeader` | 顶部导航栏 |
| `MessageList` | 消息列表容器 |
| `MessageBubble` | 单条消息气泡 |
| `LoadingIndicator` | 加载状态提示 |
| `AlertCard` | 健康提醒/偏好合规卡片（带颜色高亮）|
| `AgentTrace` | Agent 调用链路折叠面板 |
| `ChatInput` | 底部输入框 + 发送按钮 |

## 7. 文件结构

```
frontend/
├── index.html
├── package.json
├── vite.config.js
└── src/
    ├── main.jsx
    ├── App.jsx
    ├── App.css
    ├── components/
    │   ├── ChatHeader.jsx
    │   ├── ChatHeader.css
    │   ├── MessageList.jsx
    │   ├── MessageList.css
    │   ├── MessageBubble.jsx
    │   ├── MessageBubble.css
    │   ├── ChatInput.jsx
    │   ├── ChatInput.css
    │   ├── AlertCard.jsx
    │   ├── AlertCard.css
    │   ├── AgentTrace.jsx
    │   └── AgentTrace.css
    └── styles/
        └── global.css
```

## 8. 验证清单

- [ ] 页面可在 http://localhost:5173 正常打开
- [ ] 发送消息后出现加载状态
- [ ] 收到响应后正确显示 answer / plan_id / health_alerts / preference_compliance
- [ ] health_alerts 显示为黄色高亮卡片
- [ ] preference_compliance 显示为绿色高亮卡片
- [ ] 超时情况正确处理
- [ ] 多次发送消息，对话历史不丢失

---

*设计文档版本：v1.0 | 日期：2026-03-27*
