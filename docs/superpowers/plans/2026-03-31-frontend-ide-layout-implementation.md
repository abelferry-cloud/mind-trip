# Frontend IDE Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a static UI demo with three-panel IDE layout (Sidebar + Stage + Inspector), Light Apple style, Monaco Editor read-only viewer, and collapsible AI thoughts chain.

**Architecture:** Vite + React 18 + TypeScript with Shadcn/UI components. Three-panel layout with resizable sidebars. Pure UI demo with mock data.

**Tech Stack:** Vite, React 18, TypeScript, Tailwind CSS, Shadcn/UI, Monaco Editor (@monaco-editor/react), Lucide React

---

## File Structure

```
front/
├── index.html
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
├── tsconfig.json
├── components.json
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── index.css
    ├── components/
    │   ├── layout/
    │   │   ├── AppShell.tsx       # Three-panel layout container
    │   │   ├── TopBar.tsx         # Fixed top bar
    │   │   ├── Sidebar.tsx        # Left: nav + session list
    │   │   ├── Stage.tsx          # Center: chat messages
    │   │   └── Inspector.tsx      # Right: Monaco Editor
    │   ├── ui/                    # Shadcn components
    │   │   ├── button.tsx
    │   │   ├── input.tsx
    │   │   ├── tabs.tsx
    │   │   ├── scroll-area.tsx
    │   │   └── accordion.tsx
    │   └── chat/
    │       ├── MessageBubble.tsx   # Message bubble
    │       ├── ChatInput.tsx       # Input area
    │       └── ThoughtsChain.tsx   # Collapsible thoughts
    ├── data/
    │   └── mockData.ts            # Mock messages and files
    └── lib/
        └── utils.ts               # Shadcn cn() utility
```

---

## Task 1: Initialize Vite Project

**Files:**
- Create: `front/package.json`
- Create: `front/vite.config.ts`
- Create: `front/tsconfig.json`
- Create: `front/tailwind.config.js`
- Create: `front/postcss.config.js`
- Create: `front/index.html`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "front",
  "private": true,
  "version": "0.0.1",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
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

- [ ] **Step 2: Create vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

- [ ] **Step 3: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 4: Create tsconfig.node.json**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 5: Create tailwind.config.js**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        accent: {
          DEFAULT: '#4A6CF7',
          hover: '#3b5ce4',
          muted: 'rgba(74, 108, 247, 0.1)',
        },
        background: {
          primary: '#ffffff',
          secondary: '#f5f5f7',
          tertiary: '#fafafa',
        },
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
```

- [ ] **Step 6: Create postcss.config.js**

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **Step 7: Create index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>mini OpenClaw</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 8: Install dependencies**

Run: `cd front && npm install`
Expected: Package installation completes

- [ ] **Step 9: Commit**

```bash
cd front && git init && git add package.json vite.config.ts tsconfig.json tailwind.config.js postcss.config.js index.html && git commit -m "feat(front): initialize Vite project with React + TypeScript + Tailwind"
```

---

## Task 2: Set Up Shadcn/UI Components

**Files:**
- Create: `front/components.json`
- Create: `front/src/lib/utils.ts`
- Create: `front/src/index.css`
- Create: `front/src/components/ui/button.tsx`
- Create: `front/src/components/ui/input.tsx`
- Create: `front/src/components/ui/tabs.tsx`
- Create: `front/src/components/ui/scroll-area.tsx`
- Create: `front/src/components/ui/accordion.tsx`

- [ ] **Step 1: Create components.json (Shadcn config)**

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "default",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.js",
    "css": "src/index.css",
    "baseColor": "slate",
    "cssVariables": true
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils"
  }
}
```

- [ ] **Step 2: Create lib/utils.ts**

```typescript
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

- [ ] **Step 3: Create index.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --bg-primary: #ffffff;
  --bg-secondary: #f5f5f7;
  --bg-tertiary: #fafafa;
  --border: rgba(0, 0, 0, 0.08);
  --text-primary: #1d1d1f;
  --text-secondary: #86868b;
  --accent: #4A6CF7;
  --accent-hover: #3b5ce4;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--bg-secondary);
  color: var(--text-primary);
  margin: 0;
  padding: 0;
}
```

- [ ] **Step 4: Create ui/button.tsx**

```typescript
import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-accent text-white hover:bg-accent-hover",
        ghost: "hover:bg-background-secondary",
        outline: "border border-[var(--border)] bg-transparent hover:bg-background-secondary",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-md px-8",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
```

- [ ] **Step 5: Create ui/input.tsx**

```typescript
import * as React from "react"
import { cn } from "@/lib/utils"

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-9 w-full rounded-md border border-[var(--border)] bg-background-primary px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-[var(--text-secondary)] focus-visible:outline-none focus-visible:border-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input }
```

- [ ] **Step 6: Create ui/tabs.tsx**

```typescript
import * as React from "react"
import * as TabsPrimitive from "@radix-ui/react-tabs"
import { cn } from "@/lib/utils"

const Tabs = TabsPrimitive.Root

const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn(
      "inline-flex h-9 items-center justify-center rounded-lg bg-background-secondary p-1 text-[var(--text-secondary)]",
      className
    )}
    {...props}
  />
))
TabsList.displayName = TabsPrimitive.List.displayName

const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background-primary data-[state=active]:text-[var(--text-primary)] data-[state=active]:shadow",
      className
    )}
    {...props}
  />
))
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName

const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn(
      "mt-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2",
      className
    )}
    {...props}
  />
))
TabsContent.displayName = TabsPrimitive.Content.displayName

export { Tabs, TabsList, TabsTrigger, TabsContent }
```

- [ ] **Step 7: Create ui/scroll-area.tsx**

```typescript
import * as React from "react"
import * as ScrollAreaPrimitive from "@radix-ui/react-scroll-area"
import { cn } from "@/lib/utils"

const ScrollArea = React.forwardRef<
  React.ElementRef<typeof ScrollAreaPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof ScrollAreaPrimitive.Root>
>(({ className, children, ...props }, ref) => (
  <ScrollAreaPrimitive.Root
    ref={ref}
    className={cn("relative overflow-hidden", className)}
    {...props}
  >
    <ScrollAreaPrimitive.Viewport className="h-full w-full rounded-[inherit]">
      {children}
    </ScrollAreaPrimitive.Viewport>
    <ScrollBar />
    <ScrollAreaPrimitive.Corner />
  </ScrollAreaPrimitive.Root>
))
ScrollArea.displayName = ScrollAreaPrimitive.Root.displayName

const ScrollBar = React.forwardRef<
  React.ElementRef<typeof ScrollAreaPrimitive.ScrollAreaScrollbar>,
  React.ComponentPropsWithoutRef<typeof ScrollAreaPrimitive.ScrollAreaScrollbar>
>(({ className, orientation = "vertical", ...props }, ref) => (
  <ScrollAreaPrimitive.ScrollAreaScrollbar
    ref={ref}
    orientation={orientation}
    className={cn(
      "flex touch-none select-none transition-colors",
      orientation === "vertical" &&
        "h-full w-2 border-l border-l-transparent p-[1px]",
      orientation === "horizontal" &&
        "h-2 flex-col border-t border-t-transparent p-[1px]",
      className
    )}
    {...props}
  >
    <ScrollAreaPrimitive.ScrollAreaThumb className="relative flex-1 rounded-full bg-[var(--border)]" />
  </ScrollAreaPrimitive.ScrollAreaScrollbar>
))
ScrollBar.displayName = ScrollAreaPrimitive.ScrollAreaScrollbar.displayName

export { ScrollArea, ScrollBar }
```

- [ ] **Step 8: Create ui/accordion.tsx**

```typescript
import * as React from "react"
import * as AccordionPrimitive from "@radix-ui/react-accordion"
import { ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"

const Accordion = AccordionPrimitive.Root

const AccordionItem = React.forwardRef<
  React.ElementRef<typeof AccordionPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof AccordionPrimitive.Item>
>(({ className, ...props }, ref) => (
  <AccordionPrimitive.Item
    ref={ref}
    className={cn("border-b border-[var(--border)]", className)}
    {...props}
  />
))
AccordionItem.displayName = "AccordionItem"

const AccordionTrigger = React.forwardRef<
  React.ElementRef<typeof AccordionPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof AccordionPrimitive.Trigger>
>(({ className, children, ...props }, ref) => (
  <AccordionPrimitive.Header className="flex">
    <AccordionPrimitive.Trigger
      ref={ref}
      className={cn(
        "flex flex-1 items-center justify-between py-4 text-sm font-medium transition-all hover:text-[var(--accent)] [&[data-state=open]>svg]:rotate-180",
        className
      )}
      {...props}
    >
      {children}
      <ChevronDown className="h-4 w-4 shrink-0 text-[var(--text-secondary)] transition-transform duration-200" />
    </AccordionPrimitive.Trigger>
  </AccordionPrimitive.Header>
))
AccordionTrigger.displayName = AccordionPrimitive.Trigger.displayName

const AccordionContent = React.forwardRef<
  React.ElementRef<typeof AccordionPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof AccordionPrimitive.Content>
>(({ className, children, ...props }, ref) => (
  <AccordionPrimitive.Content
    ref={ref}
    className="overflow-hidden text-sm data-[state=closed]:animate-accordion-up data-[state=open]:animate-accordion-down"
    {...props}
  >
    <div className={cn("pb-4 pt-0", className)}>{children}</div>
  </AccordionPrimitive.Content>
))
AccordionContent.displayName = AccordionContent.displayName

export { Accordion, AccordionItem, AccordionTrigger, AccordionContent }
```

- [ ] **Step 9: Add accordion animations to index.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@keyframes accordion-down {
  from {
    height: 0;
  }
  to {
    height: var(--radix-accordion-content-height);
  }
}

@keyframes accordion-up {
  from {
    height: var(--radix-accordion-content-height);
  }
  to {
    height: 0;
  }
}

.animate-accordion-down {
  animation: accordion-down 0.2s ease-out;
}

.animate-accordion-up {
  animation: accordion-up 0.2s ease-out;
}
```

- [ ] **Step 10: Install Radix dependencies**

Run: `cd front && npm install @radix-ui/react-slot @radix-ui/react-accordion @radix-ui/react-tabs @radix-ui/react-scroll-area`
Expected: Package installation completes

- [ ] **Step 11: Commit**

```bash
cd front && git add components.json src/lib/utils.ts src/index.css src/components/ui/*.tsx && git commit -m "feat(front): set up Shadcn/UI components (button, input, tabs, scroll-area, accordion)"
```

---

## Task 3: Create Mock Data

**Files:**
- Create: `front/src/data/mockData.ts`

- [ ] **Step 1: Create mockData.ts**

```typescript
export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  thoughts?: string[]
}

export interface Session {
  id: string
  title: string
  messages: Message[]
}

export const mockSession: Session = {
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
      content: '好的，我来为您规划杭州3日游。让我先了解一下您的偏好，然后为您合理分配预算。',
      timestamp: '10:30 AM',
      thoughts: [
        '用户需要规划杭州3日游，预算2000元',
        '需要考虑用户的美食偏好',
        '计算每日预算分配：交通200元/天，住宿400元/天，餐饮150元/天，门票200元/天',
        '规划景点路线顺序：Day1西湖景区，Day2灵隐寺+宋城，Day3千岛湖',
      ],
    },
    {
      id: 'msg-003',
      role: 'assistant',
      content: `📍 **杭州3日游行程规划**

**Day 1: 西湖景区**
- 8:00 苏堤春晓
- 10:00 花港观鱼
- 12:00 知味观午餐
- 14:00 雷峰塔
- 18:00 西湖音乐喷泉

**Day 2: 文化之旅**
- 8:30 灵隐寺
- 11:30 龙井问茶
- 14:00 宋城千古情
- 18:00 河坊街美食

**Day 3: 自然风光**
- 7:00 出发千岛湖
- 9:00 游船登岛
- 14:00 返回市区

💰 **预算分配：¥2000**
- 交通: ¥400
- 住宿: ¥600 (2晚)
- 餐饮: ¥500
- 门票: ¥500`,
      timestamp: '10:31 AM',
    },
  ],
}

export const mockSessions: Session[] = [
  mockSession,
  {
    id: 'session-002',
    title: '上海周末游',
    messages: [
      {
        id: 'msg-101',
        role: 'user',
        content: '上海2日游推荐',
        timestamp: '昨天',
      },
    ],
  },
  {
    id: 'session-003',
    title: '成都美食之旅',
    messages: [
      {
        id: 'msg-201',
        role: 'user',
        content: '成都美食推荐',
        timestamp: '3天前',
      },
    ],
  },
]

export const mockInspectorFiles: Record<string, string> = {
  'SOUL.md': `# Soul - 核心人格

你是 Smart Travel Journal 的核心智能助手。你的使命是：

## 核心原则

1. **用户至上**：始终以用户需求为中心
2. **专业规划**：提供科学合理的旅行规划
3. **透明沟通**：清晰展示决策过程和理由
4. **持续学习**：根据用户反馈不断优化

## 行为准则

- 使用清晰、友好的语言
- 主动提供有用的小贴士
- 尊重用户的时间和预算
- 保护用户隐私和数据安全`,
  'IDENTITY.md': `# Identity - 身份定义

**名称**: Smart Travel Journal 智能助手

**角色**: 你的专业旅行规划顾问

**特长**:
- 🗺️ 景点推荐与路线规划
- 🍜 当地美食探索
- 🏨 住宿选择建议
- 💰 预算优化方案
- ⚠️ 健康与安全提醒

**沟通风格**:
- 亲切专业
- 条理清晰
- 主动积极
- 诚实可靠`,
  'AGENTS.md': `# Agents - 多Agent协作规则

## Agent 架构

### PlanningAgent (主管)
- 职责：协调整个规划流程
- 入口：唯一接受用户请求的Agent

### PreferenceAgent (偏好管理)
- 职责：解析并更新用户偏好
- 权限：唯一可写入长期记忆的Agent

### BudgetAgent (预算计算)
- 职责：预算计算与验证
- 触发：超预算时重新规划

### TravelPlannerAgent (旅行规划)
- 职责：景点、餐厅、酒店、路线规划
- 整合：替代原有的多个专项Agent

## 协作流程

1. PlanningAgent 接收并解析用户请求
2. PreferenceAgent 更新长期记忆
3. 并行执行：TravelPlannerAgent + BudgetAgent
4. 生成最终行程方案`,
  'MEMORY.md': `# Memory - 长期记忆

## 用户偏好

- **出行风格**: 深度体验 > 走马观花
- **预算范围**: ¥1500-2500/天
- **美食偏好**: 浙菜、川菜、粤菜
- **住宿偏好**: 经济型酒店，干净舒适

## 历史行程

| 日期 | 目的地 | 天数 | 评价 |
|------|--------|------|------|
| 2026-03-15 | 上海 | 2日 | ⭐⭐⭐⭐⭐ |
| 2026-02-28 | 苏州 | 1日 | ⭐⭐⭐⭐ |
| 2026-01-20 | 三亚 | 5日 | ⭐⭐⭐⭐⭐ |

## 健康提醒

- 用户对海鲜轻微过敏
- 行走时间过长时需注意休息`,
}
```

- [ ] **Step 2: Commit**

```bash
cd front && git add src/data/mockData.ts && git commit -m "feat(front): add mock data for sessions and inspector files"
```

---

## Task 4: Build Layout Components

**Files:**
- Create: `front/src/components/layout/TopBar.tsx`
- Create: `front/src/components/layout/Sidebar.tsx`
- Create: `front/src/components/layout/Stage.tsx`
- Create: `front/src/components/layout/Inspector.tsx`
- Create: `front/src/components/layout/AppShell.tsx`

- [ ] **Step 1: Create TopBar.tsx**

```typescript
import { ExternalLink } from 'lucide-react'

export function TopBar() {
  return (
    <header className="fixed top-0 left-0 right-0 h-12 bg-background-primary/80 backdrop-blur-sm border-b border-[var(--border)] flex items-center justify-between px-6 z-50">
      <div className="flex-1" />
      <h1 className="text-base font-semibold text-[var(--text-primary)]">
        mini OpenClaw
      </h1>
      <div className="flex-1 flex justify-end">
        <a
          href="https://fufan.ai"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-sm text-[var(--text-secondary)] hover:text-[var(--accent)] transition-colors"
        >
          赋范空间
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>
    </header>
  )
}
```

- [ ] **Step 2: Create Sidebar.tsx**

```typescript
import { MessageSquare, Brain, Sparkles } from 'lucide-react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { mockSessions } from '@/data/mockData'
import { cn } from '@/lib/utils'

type Tab = 'chat' | 'memory' | 'skills'

interface SidebarProps {
  activeTab: Tab
  onTabChange: (tab: Tab) => void
  activeSessionId: string
  onSessionChange: (id: string) => void
}

const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'chat', label: 'Chat', icon: <MessageSquare className="w-4 h-4" /> },
  { id: 'memory', label: 'Memory', icon: <Brain className="w-4 h-4" /> },
  { id: 'skills', label: 'Skills', icon: <Sparkles className="w-4 h-4" /> },
]

export function Sidebar({
  activeTab,
  onTabChange,
  activeSessionId,
  onSessionChange,
}: SidebarProps) {
  return (
    <aside className="w-[260px] min-w-[200px] max-w-[400px] bg-background-secondary border-r border-[var(--border)] flex flex-col h-full">
      {/* Navigation Tabs */}
      <div className="flex border-b border-[var(--border)]">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={cn(
              'flex-1 flex flex-col items-center gap-1 py-3 text-xs transition-colors',
              activeTab === tab.id
                ? 'text-[var(--accent)] border-b-2 border-[var(--accent)]'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            )}
          >
            {tab.icon}
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Session List */}
      <ScrollArea className="flex-1">
        <div className="p-3">
          <h3 className="text-xs font-medium text-[var(--text-secondary)] mb-2 px-2">
            会话列表
          </h3>
          <div className="space-y-1">
            {mockSessions.map((session) => (
              <button
                key={session.id}
                onClick={() => onSessionChange(session.id)}
                className={cn(
                  'w-full text-left px-3 py-2 rounded-lg text-sm transition-colors',
                  activeSessionId === session.id
                    ? 'bg-accent-muted text-[var(--accent)]'
                    : 'text-[var(--text-primary)] hover:bg-background-tertiary'
                )}
              >
                {session.title}
              </button>
            ))}
          </div>
        </div>
      </ScrollArea>
    </aside>
  )
}
```

- [ ] **Step 3: Create Stage.tsx**

```typescript
import { ScrollArea } from '@/components/ui/scroll-area'
import { MessageBubble } from '@/components/chat/MessageBubble'
import { ChatInput } from '@/components/chat/ChatInput'
import { mockSession } from '@/data/mockData'

interface StageProps {
  sessionId: string
}

export function Stage({ sessionId }: StageProps) {
  // In real app, would fetch session by ID
  const session = mockSession

  return (
    <main className="flex-1 flex flex-col bg-background-primary min-w-[400px] h-full">
      <ScrollArea className="flex-1 p-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {session.messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
        </div>
      </ScrollArea>
      <div className="p-4 border-t border-[var(--border)]">
        <div className="max-w-3xl mx-auto">
          <ChatInput />
        </div>
      </div>
    </main>
  )
}
```

- [ ] **Step 4: Create Inspector.tsx**

```typescript
import { useState } from 'react'
import Editor from '@monaco-editor/react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { mockInspectorFiles } from '@/data/mockData'

const fileNames = ['SOUL.md', 'IDENTITY.md', 'AGENTS.md', 'MEMORY.md']

export function Inspector() {
  const [activeFile, setActiveFile] = useState('SOUL.md')

  return (
    <aside className="w-[380px] min-w-[280px] max-w-[600px] bg-background-tertiary border-l border-[var(--border)] flex flex-col h-full">
      <Tabs value={activeFile} onValueChange={setActiveFile} className="flex-1 flex flex-col">
        <TabsList className="w-full justify-start rounded-none border-b border-[var(--border)] bg-background-secondary p-1">
          {fileNames.map((name) => (
            <TabsTrigger
              key={name}
              value={name}
              className="text-xs data-[state=active]:text-[var(--accent)]"
            >
              {name}
            </TabsTrigger>
          ))}
        </TabsList>
        {fileNames.map((name) => (
          <TabsContent key={name} value={name} className="flex-1 m-0">
            <Editor
              height="100%"
              language="markdown"
              value={mockInspectorFiles[name]}
              theme="vs"
              options={{
                readOnly: true,
                minimap: { enabled: false },
                lineNumbers: 'off',
                glyphMargin: false,
                folding: false,
                scrollBeyondLastLine: false,
                wordWrap: 'on',
                fontSize: 13,
                fontFamily: 'JetBrains Mono, Fira Code, monospace',
                renderLineHighlight: 'none',
                scrollbar: {
                  verticalScrollbarSize: 8,
                  horizontalScrollbarSize: 8,
                },
              }}
            />
          </TabsContent>
        ))}
      </Tabs>
    </aside>
  )
}
```

- [ ] **Step 5: Create AppShell.tsx**

```typescript
import { useState } from 'react'
import { TopBar } from './TopBar'
import { Sidebar } from './Sidebar'
import { Stage } from './Stage'
import { Inspector } from './Inspector'

type Tab = 'chat' | 'memory' | 'skills'

export function AppShell() {
  const [activeTab, setActiveTab] = useState<Tab>('chat')
  const [activeSessionId, setActiveSessionId] = useState('session-001')

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-background-secondary">
      <TopBar />
      <div className="flex flex-1 pt-12 overflow-hidden">
        <Sidebar
          activeTab={activeTab}
          onTabChange={setActiveTab}
          activeSessionId={activeSessionId}
          onSessionChange={setActiveSessionId}
        />
        <Stage sessionId={activeSessionId} />
        <Inspector />
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Commit**

```bash
cd front && git add src/components/layout/*.tsx && git commit -m "feat(front): build layout components (TopBar, Sidebar, Stage, Inspector, AppShell)"
```

---

## Task 5: Build Chat Components

**Files:**
- Create: `front/src/components/chat/MessageBubble.tsx`
- Create: `front/src/components/chat/ChatInput.tsx`
- Create: `front/src/components/chat/ThoughtsChain.tsx`

- [ ] **Step 1: Create ThoughtsChain.tsx**

```typescript
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'

interface ThoughtsChainProps {
  thoughts: string[]
}

export function ThoughtsChain({ thoughts }: ThoughtsChainProps) {
  return (
    <Accordion type="single" collapsible className="w-full">
      <AccordionItem value="thoughts" className="border-none">
        <AccordionTrigger className="text-xs text-[var(--text-secondary)] hover:no-underline py-2">
          <span className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />
            思考过程 ({thoughts.length}步)
          </span>
        </AccordionTrigger>
        <AccordionContent>
          <div className="bg-background-secondary rounded-lg p-3 space-y-2">
            {thoughts.map((thought, index) => (
              <div key={index} className="flex gap-2 text-sm">
                <span className="text-[var(--accent)] font-mono text-xs">
                  {String(index + 1).padStart(2, '0')}
                </span>
                <span className="text-[var(--text-secondary)]">{thought}</span>
              </div>
            ))}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  )
}
```

- [ ] **Step 2: Create MessageBubble.tsx**

```typescript
import { User, Bot } from 'lucide-react'
import { Message } from '@/data/mockData'
import { ThoughtsChain } from './ThoughtsChain'
import { cn } from '@/lib/utils'

interface MessageBubbleProps {
  message: Message
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex gap-3', isUser ? 'flex-row-reverse' : 'flex-row')}>
      {/* Avatar */}
      <div
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center shrink-0',
          isUser ? 'bg-accent' : 'bg-background-secondary'
        )}
      >
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-[var(--text-secondary)]" />
        )}
      </div>

      {/* Content */}
      <div className={cn('flex flex-col gap-2 max-w-[80%]', isUser ? 'items-end' : 'items-start')}>
        <div
          className={cn(
            'rounded-2xl px-4 py-2.5 text-sm',
            isUser
              ? 'bg-accent text-white rounded-tr-sm'
              : 'bg-background-secondary text-[var(--text-primary)] rounded-tl-sm'
          )}
        >
          {message.content.split('\n').map((line, i) => (
            <p key={i} className={line.startsWith('#') ? 'font-bold' : ''}>
              {line}
            </p>
          ))}
        </div>
        <span className="text-xs text-[var(--text-secondary)]">{message.timestamp}</span>

        {/* Thoughts Chain (Assistant only) */}
        {!isUser && message.thoughts && message.thoughts.length > 0 && (
          <ThoughtsChain thoughts={message.thoughts} />
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create ChatInput.tsx**

```typescript
import { useState } from 'react'
import { Send } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

export function ChatInput() {
  const [value, setValue] = useState('')

  const handleSend = () => {
    if (!value.trim()) return
    // Mock: In real app, would send to backend
    console.log('Sending:', value)
    setValue('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex gap-2">
      <Input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="请描述你的出行需求..."
        className="flex-1"
      />
      <Button onClick={handleSend} disabled={!value.trim()} size="icon">
        <Send className="w-4 h-4" />
      </Button>
    </div>
  )
}
```

- [ ] **Step 4: Commit**

```bash
cd front && git add src/components/chat/*.tsx && git commit -m "feat(front): build chat components (MessageBubble, ChatInput, ThoughtsChain)"
```

---

## Task 6: Wire Up App Entry

**Files:**
- Create: `front/src/main.tsx`
- Create: `front/src/App.tsx`

- [ ] **Step 1: Create main.tsx**

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import { App } from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
```

- [ ] **Step 2: Create App.tsx**

```typescript
import { AppShell } from './components/layout/AppShell'

export function App() {
  return <AppShell />
}
```

- [ ] **Step 3: Test build**

Run: `cd front && npm run build`
Expected: Build completes without errors

- [ ] **Step 4: Test dev server**

Run: `cd front && npm run dev`
Expected: Dev server starts at http://localhost:5173

- [ ] **Step 5: Commit**

```bash
cd front && git add src/main.tsx src/App.tsx && git commit -m "feat(front): wire up app entry point"
```

---

## Final Verification

- [ ] **Step 1: Verify three-panel layout renders correctly**
  - Sidebar (260px) on left with navigation tabs and session list
  - Stage (flex) in center with messages and input
  - Inspector (380px) on right with tabs and Monaco Editor

- [ ] **Step 2: Verify TopBar**
  - "mini OpenClaw" centered
  - "赋范空间" link to fufan.ai on right

- [ ] **Step 3: Verify Monaco Editor**
  - Shows SOUL.md content by default
  - Read-only mode
  - Light theme

- [ ] **Step 4: Verify ThoughtsChain**
  - Shows "思考过程 (N步)" collapsed by default
  - Expands to show numbered thought steps

- [ ] **Step 5: Verify message bubbles**
  - User messages right-aligned with accent background
  - Assistant messages left-aligned with secondary background
  - Timestamps displayed

---

## Dependencies Summary

```bash
cd front && npm install
npm install @radix-ui/react-slot @radix-ui/react-accordion @radix-ui/react-tabs @radix-ui/react-scroll-area
npm install @monaco-editor/react lucide-react class-variance-authority clsx tailwind-merge
npm install -D @vitejs/plugin-react typescript vite tailwindcss postcss autoprefixer
```
