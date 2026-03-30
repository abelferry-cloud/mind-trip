# Smart Travel Journal - Agent UI Redesign Design

**Date:** 2026-03-30
**Status:** Draft v2 (Review Iteration 1)
**Version:** 1.1

---

## 1. Overview

### 1.1 Background

Smart Travel Journal is a multi-agent trip planning system based on LangChain. Currently only implements intelligent chat functionality. The UI needs redesign to:

1. Improve visual design and user experience
2. Support future extensions (attractions, routes, budget, hotels, restaurants)
3. Visualize multi-agent collaboration
4. Display memory and knowledge management

### 1.2 Design Philosophy

- **Private AI**: Reference OpenClaw's design philosophy
- **File as Database, Full Transparency**: All memory, context, and agent states should be visible to the user
- **Hybrid Style**: Developer tool aesthetics + modern assistant fluidity

### 1.3 Design Goals

| Goal | Description |
|------|-------------|
| Progressive Enhancement | Incrementally improve existing three-panel architecture |
| Visual Hierarchy | Balance information transparency with conversational fluency |
| Extension Ready | Reserve interfaces for future features without major refactoring |
| Agent Transparency | Make multi-agent collaboration visible and understandable |

---

## 2. Design Language

### 2.1 Color Palette

**Retain existing Light Theme** (aligned with current `global.css`):

```css
:root {
  /* Backgrounds - Light Mode */
  --bg-deep: #f8fafc;           /* Deepest background */
  --bg-primary: #ffffff;         /* Primary panels */
  --bg-secondary: #f1f5f9;     /* Secondary surfaces */
  --bg-elevated: #ffffff;       /* Elevated elements */
  --bg-hover: #e2e8f0;          /* Hover state */
  --bg-active: #cbd5e1;        /* Active/selected state */

  /* Borders */
  --border-subtle: rgba(0, 0, 0, 0.04);
  --border-default: rgba(0, 0, 0, 0.08);
  --border-strong: rgba(0, 0, 0, 0.12);

  /* Text */
  --text-primary: #0f172a;
  --text-secondary: #475569;
  --text-muted: #94a3b8;
  --text-disabled: #cbd5e1;

  /* Accent - Warm Amber */
  --accent-primary: #d97706;     /* Primary amber */
  --accent-hover: #b45309;
  --accent-muted: rgba(217, 119, 6, 0.1);
  --accent-subtle: rgba(217, 119, 6, 0.05);

  /* Status Colors */
  --success: #16a34a;
  --warning: #d97706;
  --error: #dc2626;
  --info: #2563eb;

  /* Agent Colors (用于多Agent可视化) */
  --agent-supervisor: #8b5cf6;   /* Purple - Supervisor */
  --agent-attractions: #f59e0b;  /* Amber - AttractionsAgent */
  --agent-route: #10b981;        /* Emerald - RouteAgent */
  --agent-budget: #ef4444;       /* Red - BudgetAgent */
  --agent-food: #f97316;         /* Orange - FoodAgent */
  --agent-hotel: #3b82f6;        /* Blue - HotelAgent */
  --agent-preference: #ec4899;   /* Pink - PreferenceAgent */
}
```

### 2.2 Typography

```css
:root {
  --font-ui: 'Plus Jakarta Sans', -apple-system, sans-serif;  /* Match existing */
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

  /* Font Sizes */
  --text-xs: 11px;
  --text-sm: 12px;
  --text-base: 14px;           /* Match existing */
  --text-lg: 16px;
  --text-xl: 18px;
  --text-2xl: 24px;
}
```

### 2.3 Spacing & Radius

```css
:root {
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;

  /* Match existing global.css */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --radius-xl: 12px;
}
```

### 2.4 Motion & Animation

```css
:root {
  --transition-fast: 150ms ease;
  --transition-normal: 250ms ease;
  --transition-slow: 400ms ease;

  /* Animation Keyframes */
  --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
}
```

**Animation Principles:**
- Message appearance: `slideUp` 300ms with stagger
- Panel transitions: 250ms ease-out
- Agent status changes: 150ms with subtle pulse
- Loading states: Pulsing dots animation

---

## 3. Layout Architecture

### 3.1 Three-Panel Structure (Retained & Enhanced)

```
┌─────────────────────────────────────────────────────────────────┐
│                          App Container                          │
├──────────┬─────────────────────────────────┬────────────────────┤
│          │                                 │                    │
│ Sidebar  │           Stage                 │    Inspector       │
│ (260px)  │         (flex: 1)               │     (380px)        │
│          │                                 │                    │
│          │  ┌─────────────────────────┐    │                    │
│ Sessions │  │      Messages           │    │  ┌────────────┐  │
│          │  │      (scrollable)       │    │  │ Tabs        │  │
│          │  │                         │    │  ├────────────┤  │
│          │  │  ┌─────────────────┐   │    │  │            │  │
│          │  │  │ Agent Workbench │   │    │  │  Content   │  │
│          │  │  │ (collapsible)   │   │    │  │            │  │
│          │  │  └─────────────────┘   │    │  │            │  │
│          │  └─────────────────────────┘    │  └────────────┘  │
│          │  ┌─────────────────────────┐    │                    │
│          │  │      Input Area          │    │                    │
├──────────┴──┴─────────────────────────┴────┴────────────────────┤
│              Resizable Handles (4px)                             │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Panel Specifications

| Panel | Min Width | Max Width | Default Width | Resizable |
|-------|-----------|-----------|----------------|-----------|
| Sidebar | 180px | 400px | 260px | Yes |
| Stage | 400px | - | flex: 1 | No |
| Inspector | 280px | 600px | 380px | Yes |

### 3.3 Sidebar Enhancement - Feature Cards Area

**Location:** Bottom of Sidebar, above session list
**Behavior:** Collapsible, shows future feature entry points

```jsx
// Future Feature Card (预留)
const featureCards = [
  { id: 'attractions', icon: '🗺️', label: '景点推荐', status: 'coming_soon' },
  { id: 'route', icon: '📍', label: '路线规划', status: 'coming_soon' },
  { id: 'budget', icon: '💰', label: '预算控制', status: 'coming_soon' },
  { id: 'food', icon: '🍜', label: '美食推荐', status: 'coming_soon' },
  { id: 'hotel', icon: '🏨', label: '酒店预订', status: 'coming_soon' },
];
```

**Visual Design:**
- Card size: Full width, 48px height
- Icon + Label + Status badge
- Coming soon: Muted appearance with lock icon
- Active: Full color with subtle glow

---

## 4. Component Specifications

### 4.1 Agent Workbench (Stage 内嵌)

**Purpose:** Display multi-agent collaboration status in real-time

**Location:** Below message bubble, before input area (collapsible per message)

**Structure:**
```
┌─────────────────────────────────────────────────────────────┐
│ ◇ Agent Workbench                              [−] [×]     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌───────┐ │
│  │Supervisor│ -> │Attractions│ -> │ Route   │ -> │Budget │ │
│  │  ●━━    │    │  ●━━    │    │  ●━━   │    │  ✓   │ │
│  └─────────┘    └─────────┘    └─────────┘    └───────┘ │
│                                                             │
│  ┌─ Current Step ──────────────────────────────────────┐  │
│  │ 🔄 RouteAgent: 正在计算最优路线...                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─ Memory Update ──────────────────────────────────────┐  │
│  │ 📝 PreferenceAgent: 已更新用户偏好 "喜欢西湖周边景点"   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Agent Status Icons:**
| Status | Icon | Color |
|--------|------|-------|
| Idle | ○ | --text-muted |
| Running | ◐ | --accent-primary (pulsing) |
| Success | ● | --success |
| Error | ● | --error |

**Interaction:**
- Click header to collapse/expand
- Hover agent node to show tooltip with details
- Click "View Details" to expand full trace

### 4.2 Inspector Tabs Redesign

**Tab Categories:**

| Tab | Content | Priority |
|-----|---------|----------|
| SOUL.md | Core personality and principles | Current |
| IDENTITY.md | Agent identity template | Current |
| AGENTS.md | Multi-agent coordination rules | Current |
| Memory | Session & long-term memory | **New** |
| Preferences | User preference settings | **New (预留)** |
| Files | Browse all workspace files | **New (预留)** |
| Settings | App settings | **New (预留)** |

**Memory Tab Design:**
```
┌─ Memory ─────────────────────────────────────────────────┐
│                                                         │
│  ┌─ Session Context ────────────────────────────────┐   │
│  │ 🟢 Active for 23 messages                        │   │
│  │ Last: "帮我规划杭州3日游"                          │   │
│  └───────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─ Long-term Memory ───────────────────────────────┐   │
│  │ 📌 Key Preferences                                 │   │
│  │   • 喜欢自然风光 > 城市景观                         │   │
│  │   • 预算范围: ¥2000-3000/天                        │   │
│  │   • 美食偏好: 川菜、浙菜                           │   │
│  │                                                  │   │
│  │ 📅 Past Trips                                     │   │
│  │   • 2026-03-15: 上海2日游                         │   │
│  │   • 2026-02-28: 苏州一日游                        │   │
│  └───────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─ Actions ────────────────────────────────────────┐   │
│  │ [+ Add Preference]  [Edit Memory]  [Export]     │   │
│  └───────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 4.3 Enhanced Message Bubble

**Current:** Simple bubble with avatar
**Enhanced:**
```
┌──────────────────────────────────────────────────────┐
│ [Avatar]  Assistant          12:34 PM              │
├──────────────────────────────────────────────────────┤
│                                                      │
│  好的，我来为你规划杭州3日游...                        │
│                                                      │
│  📍 **Day 1: 西湖景区**                              │
│  • 8:00 苏堤春晓                                     │
│  • 10:00 花港观鱼                                    │
│  ...                                                 │
│                                                      │
│  💰 预估预算: ¥1,200                                 │
│                                                      │
├──────────────────────────────────────────────────────┤
│ Thinking...  │  Tools...  │  [Agent Workbench ▼]  │
└──────────────────────────────────────────────────────┘
```

**Action Bar (below bubble):**
- **Thinking** - Toggle reasoning trace (like current thoughts-chain)
- **Tools** - Show tools used (if any)
- **Agent Workbench ▼** - Expand/collapse agent visualization

### 4.4 Input Area Enhancement

**Current:** Simple textarea with send button
**Enhanced:**
```
┌─────────────────────────────────────────────────────────────────┐
│ ┌───────────────────────────────────────────────────────────┐   │
│ │ 请描述你的出行需求...                                       │   │
│ │ (例如: 帮我规划杭州3日游，预算2000元)                         │   │
│ │                                                            │   │
│ │                                    ↵ Shift+Enter for new   │   │
│ └───────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐          ┌──────────┐  │
│  │ 📎   │  │ 🎯   │  │ 📍   │  │ 💰   │          │    发送   │  │
│  │文件  │  │目的地│  │景点  │  │预算  │          └──────────┘  │
│  └──────┘  └──────┘  └──────┘  └──────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

**Quick Action Chips:**
| Chip | Function | Status |
|------|----------|--------|
| 📎 文件 | Attach files | **New** |
| 🎯 目的地 | Quick destination input | **New** |
| 📍 景点 | Attraction picker | **Reserved** |
| 💰 预算 | Budget input | **Reserved** |

---

## 5. Future Extension Interface

### 5.1 Feature Module Interface

```typescript
// Feature Module Contract
interface FeatureModule {
  id: string;                    // Unique identifier
  name: string;                  // Display name
  icon: string;                  // Emoji icon
  status: 'coming_soon' | 'active' | 'disabled';
  panel: 'sidebar' | 'stage' | 'inspector' | 'modal';
  component: React.Component;     // Main component
  route?: string;                // Optional route for fullscreen mode
}

// Registration API
window.smartJournal.registerFeature({
  id: 'attractions',
  name: '景点推荐',
  icon: '🗺️',
  status: 'coming_soon',
  panel: 'sidebar',
  component: AttractionsPanel,
});
```

### 5.2 Agent Plugin Interface

```typescript
// Agent Plugin Contract
interface AgentPlugin {
  id: string;
  name: string;
  color: string;              // Agent-specific color
  icon: string;
  description: string;
  capabilities: string[];
}

// Agent Event API
window.smartJournal.agents.on('statusChange', (agentId, status) => {
  // Update Agent Workbench
});

window.smartJournal.agents.on('thinking', (agentId, thought) => {
  // Stream thinking process
});

window.smartJournal.agents.on('complete', (agentId, result) => {
  // Show completion state
});
```

### 5.3 Memory Plugin Interface

```typescript
// Memory Plugin Contract
interface MemoryPlugin {
  type: 'session' | 'longterm' | 'preference';
  read(): Promise<MemoryEntry[]>;
  write(entry: MemoryEntry): Promise<void>;
  subscribe(callback: (entry: MemoryEntry) => void): void;
}

// Usage
window.smartJournal.memory.onUpdate((entry) => {
  // Refresh Memory Tab
});
```

---

## 6. Implementation Phases

### Phase 1: UI Polish & Core Enhancement
- Refine color palette and typography
- Enhance message bubble with action bar
- Implement Agent Workbench component
- Redesign Inspector tabs

### Phase 2: Memory & Preferences
- Build Memory Tab in Inspector
- Implement preference editing UI
- Add memory visualization

### Phase 3: Feature Cards & Quick Actions
- Add Sidebar feature cards area
- Implement input area quick action chips
- Build feature module registration system

### Phase 4: Agent Visualization
- Enhance Agent Workbench with real-time updates
- Add agent collaboration graph
- Implement agent status streaming

---

## 7. API Specification

### 7.1 Agent Event Streaming API

**Existing Endpoint:** `POST /api/chat/stream`

**Description:** Reuse existing SSE streaming endpoint. Events are emitted via `StreamManager`.

**Existing Event Types (from `stream_manager.py`):**

| Event | Payload | Description |
|-------|---------|-------------|
| `agent_switch` | `{ agent: string }` | Agent changed to new agent |
| `model_switch` | `{ model: string, reason: string }` | Model changed |
| `iteration` | `{ iteration: int, max_iterations: int }` | Iteration info |
| `tool_start` | `{ tool: string, tool_call_id: string }` | Tool execution started |
| `tool_end` | `{ tool: string, summary: any, duration_ms: int }` | Tool execution completed |
| `tool_error` | `{ tool: string, error: string }` | Tool execution failed |
| `llm_start` | `{ model: string }` | LLM started processing |
| `llm_end` | `{ total_tokens: int, ... }` | LLM finished |
| `reasoning_step` | `{ step: string }` | Agent reasoning step (thinking) |
| `content_chunk` | `{ content: string }` | Streaming response content |
| `final` | `{ answer: string }` | Final complete response |
| `error` | `{ error: string }` | Error occurred |

**Frontend Subscription (via existing `EventSource` on `/api/chat/stream`):**
```typescript
// Note: SSE events come through the existing chat_stream connection
const eventSource = new EventSource('/api/chat/stream', { ... });

eventSource.addEventListener('agent_switch', (e) => {
  const data = JSON.parse(e.data);
  agentWorkbench.switchAgent(data.agent);
});

eventSource.addEventListener('reasoning_step', (e) => {
  const data = JSON.parse(e.data);
  agentWorkbench.appendThought(data.step);
});

eventSource.addEventListener('tool_start', (e) => {
  const data = JSON.parse(e.data);
  agentWorkbench.showToolRunning(data.tool);
});
```

### 7.2 Preference API Endpoints

**Existing Endpoints (from `app/api/preference.py`):**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/preference/{user_id}` | Get user preferences and history |
| PUT | `/api/preference/{user_id}` | Update a specific preference |

**GET /api/preference/{user_id} Response:**
```json
{
  "user_id": "user123",
  "preferences": {
    "preferred_cuisine": "川菜",
    "budget_range": "2000-3000/天",
    "travel_style": "自然风光"
  },
  "history_trips": [
    { "date": "2026-03-15", "destination": "上海", "duration": "2日" }
  ]
}
```

**PUT /api/preference/{user_id} Request:**
```json
{
  "key": "preferred_cuisine",
  "value": "浙菜"
}
```

### 7.3 Future Feature API (Reserved)

For future feature modules (attractions, hotels, etc.), a simple registration mechanism:

```typescript
// Frontend feature registry (no backend API needed initially)
interface FeatureModule {
  id: string;
  name: string;
  icon: string;
  status: 'coming_soon' | 'active' | 'disabled';
  panel: 'sidebar' | 'stage' | 'inspector' | 'modal';
  component?: React.Component;
}

// Static registration in component code
const featureRegistry = {
  attractions: { id: 'attractions', name: '景点推荐', icon: '🗺️', status: 'coming_soon', panel: 'sidebar' },
  route: { id: 'route', name: '路线规划', icon: '📍', status: 'coming_soon', panel: 'sidebar' },
  budget: { id: 'budget', name: '预算控制', icon: '💰', status: 'coming_soon', panel: 'sidebar' },
  food: { id: 'food', name: '美食推荐', icon: '🍜', status: 'coming_soon', panel: 'sidebar' },
  hotel: { id: 'hotel', name: '酒店预订', icon: '🏨', status: 'coming_soon', panel: 'sidebar' },
};
```

---

## 8. Technical Considerations

### 8.1 Performance
- Lazy load Inspector tabs content
- Virtualize message list for long conversations
- Debounce resize handlers (16ms)

### 7.2 Accessibility
- Maintain keyboard navigation
- ARIA labels for all interactive elements
- Focus management for modal/panel transitions

### 7.3 State Management
- Local component state for UI interactions
- React Context for shared state (theme, user preferences)
- Server state via API calls (sessions, messages, memory)

---

## 9. Open Questions

| Item | Question | Decision |
|------|----------|----------|
| Q1 | Agent Workbench 默认展开还是收起？ | 建议默认收起，用户点击展开 |
| Q2 | Feature Cards 是否需要拖拽排序？ | 第一版不需要，保持固定顺序 |
| Q3 | 是否需要暗黑/亮色模式切换？ | 后续版本考虑，当前保持亮色主题 |

---

## 10. Appendix

### A. File Structure Changes

```
frontend/src/
├── components/
│   ├── Sidebar/
│   │   ├── index.jsx
│   │   ├── SessionList.jsx
│   │   └── FeatureCards.jsx      # New
│   ├── Stage/
│   │   ├── index.jsx
│   │   ├── Messages.jsx
│   │   ├── MessageBubble.jsx     # Enhanced
│   │   ├── AgentWorkbench.jsx    # New
│   │   └── InputArea.jsx         # Enhanced
│   └── Inspector/
│       ├── index.jsx
│       ├── TabBar.jsx
│       ├── MemoryTab.jsx         # New
│       └── FileContent.jsx
├── hooks/
│   ├── useAgentEvents.js        # New
│   └── useFeatureRegistry.js    # New
└── plugins/
    └── featureRegistry.js       # New
```

### B. Color Mapping for Agents

| Agent | Color Variable | Hex |
|-------|---------------|-----|
| PlanningAgent (Supervisor) | --agent-supervisor | #8b5cf6 |
| AttractionsAgent | --agent-attractions | #f59e0b |
| RouteAgent | --agent-route | #10b981 |
| BudgetAgent | --agent-budget | #ef4444 |
| FoodAgent | --agent-food | #f97316 |
| HotelAgent | --agent-hotel | #3b82f6 |
| PreferenceAgent | --agent-preference | #ec4899 |
