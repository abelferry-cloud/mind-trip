# Frontend IDE Layout Design - Mini OpenClaw

**Date:** 2026-03-31
**Status:** Approved
**Version:** 1.0

---

## 1. Overview

Build a static UI demo for the Smart Travel Journal frontend with an IDE-style three-panel layout. This is a pure UI demonstration without backend integration.

### 1.1 Goals

- Three-panel IDE layout: Sidebar + Stage + Inspector
- Light Apple-style aesthetic (no glassmorphism)
- Monaco Editor for read-only file viewing
- Collapsible AI thoughts chain

### 1.2 Out of Scope

- Backend API integration (pure UI demo with mock data)
- Monaco Editor editing capability (read-only)
- Theme switching
- Animation effects

---

## 2. Technical Stack

| Component | Choice | Reason |
|-----------|--------|--------|
| Framework | Vite + React 18 | Lightweight, fast |
| Language | TypeScript | Type safety |
| UI Library | Shadcn/UI | Customizable components |
| Styling | Tailwind CSS | Shadcn companion |
| Icons | Lucide React | Shadcn default |
| Editor | @monaco-editor/react | Monaco for React |
| State | React useState/useContext | Lightweight |

---

## 3. File Structure

```
front/
├── index.html
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
├── components.json          # Shadcn CLI config
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── index.css             # Global styles + CSS variables
    ├── components/
    │   ├── layout/
    │   │   ├── AppShell.tsx      # Three-panel layout container
    │   │   ├── TopBar.tsx        # Fixed top bar
    │   │   ├── Sidebar.tsx       # Left: nav + session list
    │   │   ├── Stage.tsx         # Center: chat messages
    │   │   └── Inspector.tsx     # Right: Monaco Editor
    │   ├── ui/                   # Shadcn components
    │   │   ├── button.tsx
    │   │   ├── input.tsx
    │   │   ├── tabs.tsx
    │   │   ├── scroll-area.tsx
    │   │   ├── accordion.tsx
    │   │   └── resizable.tsx
    │   └── chat/
    │       ├── MessageBubble.tsx  # Message bubble
    │       ├── ChatInput.tsx      # Input area
    │       └── ThoughtsChain.tsx  # Collapsible thoughts
    ├── data/
    │   └── mockData.ts           # Mock messages and files
    └── lib/
        └── utils.ts              # Shadcn cn() utility
```

---

## 4. Layout Specifications

### 4.1 Three-Panel Structure

```
┌────────────────────────────────────────────────────────────────────┐
│  TopBar: "mini OpenClaw" (center)        "赋范空间" → fufan.ai     │
├──────────────┬─────────────────────────────────┬───────────────────┤
│              │                                 │                   │
│   Sidebar    │           Stage                 │    Inspector      │
│   (260px)    │         (flex: 1)               │     (380px)       │
│              │                                 │                   │
│ ┌──────────┐ │  ┌─────────────────────────┐   │  ┌─────────────┐ │
│ │ Chat     │ │  │                         │   │  │ Tabs:       │ │
│ │ Memory   │ │  │  Messages (scrollable)  │   │  │ SOUL.md     │ │
│ │ Skills   │ │  │                         │   │  │ IDENTITY.md │ │
│ ├──────────┤ │  │  [MessageBubble]        │   │  │ AGENTS.md   │ │
│ │          │ │  │  [ThoughtsChain ▼]      │   │  │ MEMORY.md   │ │
│ │ 会话列表  │ │  │                         │   │  ├─────────────┤ │
│ │          │ │  │  [MessageBubble]        │   │  │             │ │
│ │ • 会话1  │ │  │                         │   │  │  Monaco     │ │
│ │ • 会话2  │ │  └─────────────────────────┘   │  │  Editor     │ │
│ │ • 会话3  │ │  ┌─────────────────────────┐   │  │  (readonly) │ │
│ │          │ │  │ ChatInput               │   │  │             │ │
│ └──────────┘ │  └─────────────────────────┘   │  └─────────────┘ │
└──────────────┴─────────────────────────────────┴───────────────────┘
```

### 4.2 Panel Dimensions

| Panel | Min Width | Default Width | Resizable |
|-------|-----------|---------------|-----------|
| Sidebar | 200px | 260px | Yes (200-400px) |
| Stage | 400px | flex: 1 | No |
| Inspector | 280px | 380px | Yes (280-600px) |

### 4.3 TopBar

- Fixed position, height: 48px
- Semi-transparent background
- Center: "mini OpenClaw" text
- Right: "赋范空间" link to https://fufan.ai

---

## 5. Color Scheme

```css
/* src/index.css */
:root {
  /* Backgrounds - Light Apple Style */
  --bg-primary: #ffffff;
  --bg-secondary: #f5f5f7;
  --bg-tertiary: #fafafa;

  /* Borders */
  --border: rgba(0, 0, 0, 0.08);

  /* Text */
  --text-primary: #1d1d1f;
  --text-secondary: #86868b;

  /* Accent - Klein Blue */
  --accent: #4A6CF7;
  --accent-hover: #3b5ce4;
  --accent-muted: rgba(74, 108, 247, 0.1);

  /* Sidebar */
  --sidebar-bg: #f5f5f7;

  /* Stage */
  --stage-bg: #ffffff;

  /* Inspector */
  --inspector-bg: #fafafa;
}
```

---

## 6. Components

### 6.1 TopBar

- Fixed top navigation
- Logo text center
- External link right
- Semi-transparent backdrop

### 6.2 Sidebar

- Navigation tabs: Chat, Memory, Skills
- Session list below
- Resizable width

### 6.3 Stage

- Scrollable message list
- MessageBubble component
- ThoughtsChain collapsible component (Accordion)
- Fixed ChatInput at bottom

### 6.4 Inspector

- Tab bar for file selection (SOUL.md, IDENTITY.md, AGENTS.md, MEMORY.md)
- Monaco Editor in read-only mode
- Light theme configuration

### 6.5 ThoughtsChain

- Collapsible accordion
- Shows AI reasoning steps
- Default collapsed

---

## 7. Mock Data

### 7.1 Session

```typescript
const mockSession = {
  id: 'session-001',
  title: '杭州3日游规划',
  messages: [
    {
      id: 'msg-001',
      role: 'user',
      content: '帮我规划杭州3日游，预算2000元',
      timestamp: '10:30 AM',
    },
    {
      id: 'msg-002',
      role: 'assistant',
      content: '好的，我来为您规划杭州3日游...',
      timestamp: '10:30 AM',
      thoughts: [
        '用户需要规划杭州3日游，预算2000元',
        '需要考虑用户的美食偏好',
        '计算每日预算分配',
        '规划景点路线顺序',
      ],
    },
  ],
};
```

### 7.2 Inspector Files

```typescript
const mockFiles = {
  'SOUL.md': '# Soul\n\n我是 Smart Travel Journal...',
  'IDENTITY.md': '# Identity\n\n你是旅行规划助手...',
  'AGENTS.md': '# Agents\n\n多Agent协作规则...',
  'MEMORY.md': '# Memory\n\n用户偏好：...',
};
```

---

## 8. Implementation Checklist

- [ ] Initialize Vite + React + TypeScript project
- [ ] Configure Tailwind CSS and Shadcn/UI
- [ ] Set up Shadcn components (button, input, tabs, scroll-area, accordion)
- [ ] Install and configure Monaco Editor
- [ ] Build TopBar component
- [ ] Build Sidebar component with navigation and session list
- [ ] Build Stage component with message list and chat input
- [ ] Build Inspector component with tabs and Monaco Editor
- [ ] Build ThoughtsChain collapsible component
- [ ] Add mock data
- [ ] Verify layout and styling
- [ ] Test resizable panels

---

## 9. Dependencies

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@monaco-editor/react": "^4.6.0",
    "lucide-react": "^0.294.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.0.0",
    "@radix-ui/react-accordion": "^1.1.2",
    "@radix-ui/react-tabs": "^1.0.4",
    "@radix-ui/react-scroll-area": "^1.0.5"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0"
  }
}
```

---

*Design Document v1.0 | Date: 2026-03-31*
