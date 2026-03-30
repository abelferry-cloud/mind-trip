# Smart Travel Journal - Agent UI Redesign Design

**Date:** 2026-03-30
**Status:** Draft
**Version:** 1.0

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

Retain existing dark theme with refined amber accent:

```css
:root {
  /* Backgrounds */
  --bg-deep: #0c0e14;        /* Deepest background */
  --bg-primary: #12151e;       /* Primary panels */
  --bg-secondary: #181c28;    /* Secondary surfaces */
  --bg-elevated: #1e2332;     /* Elevated elements */
  --bg-hover: rgba(255, 255, 255, 0.04);
  --bg-active: rgba(255, 255, 255, 0.08);

  /* Borders */
  --border-subtle: rgba(255, 255, 255, 0.06);
  --border-default: rgba(255, 255, 255, 0.10);
  --border-strong: rgba(255, 255, 255, 0.16);

  /* Text */
  --text-primary: #e8eaed;
  --text-secondary: #9aa0a6;
  --text-muted: #5f6368;

  /* Accent - Amber (保留并优化) */
  --accent-primary: #d97706;    /* Primary amber */
  --accent-hover: #b45309;
  --accent-muted: rgba(217, 119, 6, 0.12);
  --accent-subtle: rgba(217, 119, 6, 0.08);

  /* Status Colors */
  --success: #34d399;
  --warning: #fbbf24;
  --error: #f87171;
  --info: #60a5fa;

  /* Agent Colors (新增 - 用于多Agent可视化) */
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
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', 'SF Mono', monospace;

  /* Font Sizes */
  --text-xs: 11px;
  --text-sm: 12px;
  --text-base: 14px;
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

  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
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

## 7. Technical Considerations

### 7.1 Performance
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

## 8. Open Questions

| Item | Question | Decision |
|------|----------|----------|
| Q1 | Agent Workbench 默认展开还是收起？ | 建议默认收起，用户点击展开 |
| Q2 | Feature Cards 是否需要拖拽排序？ | 第一版不需要，保持固定顺序 |
| Q3 | 是否需要暗黑/亮色模式切换？ | 后续版本考虑，当前保持暗黑 |

---

## 9. Appendix

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
