# Agent UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Agent UI redesign with Agent Workbench, Memory Tab, Feature Cards, and enhanced message bubbles.

**Architecture:** Progressive enhancement of existing three-panel React architecture. New components (AgentWorkbench, MemoryTab, FeatureCards) are added alongside existing components. State managed via React hooks, SSE events consumed via existing EventSource.

**Tech Stack:** React, CSS Modules (existing), SSE (existing backend)

---

## File Impact Summary

### New Files to Create
- `frontend/src/components/AgentWorkbench.jsx`
- `frontend/src/components/MemoryTab.jsx`
- `frontend/src/components/FeatureCards.jsx`
- `frontend/src/hooks/useAgentEvents.js`

### Files to Modify
- `frontend/src/App.jsx:1-274` - Add new state and integrate components
- `frontend/src/components/Stage.jsx` - Integrate AgentWorkbench, enhance messages
- `frontend/src/components/Inspector.jsx` - Add Memory tab support
- `frontend/src/components/Sidebar.jsx` - Integrate FeatureCards
- `frontend/src/styles/App.css:1-1087` - Add new component styles

---

## Phase 1: UI Polish & Core Enhancement

### Task 1: Create AgentWorkbench Component

**Files:**
- Create: `frontend/src/components/AgentWorkbench.jsx`
- Modify: `frontend/src/components/Stage.jsx:1-50`
- Test: Visual verification in browser

- [ ] **Step 1: Create AgentWorkbench.jsx**

```jsx
// frontend/src/components/AgentWorkbench.jsx
import React, { useState, useEffect } from 'react';

const AGENT_COLORS = {
  supervisor: 'var(--agent-supervisor, #8b5cf6)',
  attractions: 'var(--agent-attractions, #f59e0b)',
  route: 'var(--agent-route, #10b981)',
  budget: 'var(--agent-budget, #ef4444)',
  food: 'var(--agent-food, #f97316)',
  hotel: 'var(--agent-hotel, #3b82f6)',
  preference: 'var(--agent-preference, #ec4899)',
};

const AGENT_NAMES = {
  supervisor: 'Supervisor',
  attractions: 'Attractions',
  route: 'Route',
  budget: 'Budget',
  food: 'Food',
  hotel: 'Hotel',
  preference: 'Preference',
};

const AgentWorkbench = ({ events = [], isExpanded = false, onToggle }) => {
  const [agents, setAgents] = useState({});
  const [currentStep, setCurrentStep] = useState('');
  const [memoryUpdates, setMemoryUpdates] = useState([]);

  // Agent flow order for display
  const agentFlow = ['supervisor', 'attractions', 'route', 'budget', 'food', 'hotel', 'preference'];

  // Process SSE events
  useEffect(() => {
    events.forEach(event => {
      switch (event.type) {
        case 'agent_switch':
          setAgents(prev => ({
            ...prev,
            [event.agent]: { ...prev[event.agent], status: 'running' }
          }));
          break;
        case 'tool_start':
          setCurrentStep(`${event.tool}: Starting...`);
          break;
        case 'tool_end':
          setCurrentStep(`${event.tool}: Completed in ${event.duration_ms}ms`);
          break;
        case 'reasoning_step':
          setCurrentStep(event.step);
          break;
        case 'llm_end':
          // Mark current agent as success
          Object.keys(agents).forEach(key => {
            if (agents[key].status === 'running') {
              setAgents(prev => ({
                ...prev,
                [key]: { ...prev[key], status: 'success' }
              }));
            }
          });
          break;
        case 'error':
          setCurrentStep(`Error: ${event.error}`);
          break;
      }
    });
  }, [events]);

  const getAgentStatusIcon = (status) => {
    switch (status) {
      case 'running': return '◐';
      case 'success': return '●';
      case 'error': return '●';
      default: return '○';
    }
  };

  const getAgentStatusColor = (status, agentId) => {
    if (status === 'running') return AGENT_COLORS[agentId] || 'var(--accent-primary)';
    if (status === 'success') return 'var(--success)';
    if (status === 'error') return 'var(--error)';
    return 'var(--text-muted)';
  };

  if (!isExpanded) {
    return (
      <div className="agent-workbench-collapsed" onClick={onToggle}>
        <span className="agent-workbench-toggle">◇</span>
        <span>Agent Workbench</span>
        <button className="agent-workbench-expand-btn">▼</button>
      </div>
    );
  }

  return (
    <div className="agent-workbench">
      <div className="agent-workbench-header">
        <span className="agent-workbench-toggle">◇</span>
        <span>Agent Workbench</span>
        <div className="agent-workbench-actions">
          <button onClick={onToggle} className="agent-workbench-collapse-btn">−</button>
          <button onClick={onToggle} className="agent-workbench-close-btn">×</button>
        </div>
      </div>

      <div className="agent-workbench-body">
        {/* Agent Flow Visualization */}
        <div className="agent-flow">
          {agentFlow.map((agentId, index) => {
            const agent = agents[agentId] || { status: 'idle' };
            return (
              <React.Fragment key={agentId}>
                <div
                  className={`agent-node ${agent.status}`}
                  style={{ '--agent-color': AGENT_COLORS[agentId] }}
                  title={AGENT_NAMES[agentId]}
                >
                  <span
                    className="agent-status-icon"
                    style={{ color: getAgentStatusColor(agent.status, agentId) }}
                  >
                    {getAgentStatusIcon(agent.status)}
                  </span>
                  <span className="agent-name">{AGENT_NAMES[agentId]}</span>
                </div>
                {index < agentFlow.length - 1 && (
                  <div className="agent-connector">→</div>
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* Current Step */}
        {currentStep && (
          <div className="agent-current-step">
            <span className="step-icon">🔄</span>
            <span className="step-text">{currentStep}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default AgentWorkbench;
```

- [ ] **Step 2: Add AgentWorkbench styles to App.css**

Add before the closing `/* Loading History State */` section:

```css
/* Agent Workbench */
.agent-workbench-collapsed {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 12px;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.agent-workbench-collapsed:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.agent-workbench-toggle {
  color: var(--accent-primary);
}

.agent-workbench-expand-btn {
  margin-left: auto;
  font-size: 10px;
}

.agent-workbench {
  background: var(--bg-primary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-top: 12px;
}

.agent-workbench-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-subtle);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.agent-workbench-actions {
  margin-left: auto;
  display: flex;
  gap: 4px;
}

.agent-workbench-collapse-btn,
.agent-workbench-close-btn {
  width: 20px;
  height: 20px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  transition: all var(--transition-fast);
}

.agent-workbench-collapse-btn:hover,
.agent-workbench-close-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.agent-workbench-body {
  padding: 16px;
}

.agent-flow {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.agent-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  min-width: 72px;
  transition: all var(--transition-fast);
}

.agent-node.running {
  background: var(--accent-muted);
  box-shadow: 0 0 8px var(--agent-color, var(--accent-primary));
}

.agent-node.success {
  background: rgba(22, 163, 74, 0.1);
}

.agent-node.error {
  background: rgba(220, 38, 38, 0.1);
}

.agent-status-icon {
  font-size: 16px;
  animation: pulse 1s ease-in-out infinite;
}

.agent-node.idle .agent-status-icon {
  animation: none;
}

.agent-name {
  font-size: 10px;
  font-weight: 500;
  color: var(--text-secondary);
}

.agent-connector {
  color: var(--text-muted);
  font-size: 14px;
}

.agent-current-step {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  font-size: 12px;
  font-family: var(--font-mono);
}

.step-icon {
  font-size: 14px;
}

.step-text {
  color: var(--text-secondary);
}
```

- [ ] **Step 3: Integrate AgentWorkbench into Stage.jsx**

Modify Stage.jsx to accept and display AgentWorkbench:

Add to Stage.jsx imports:
```jsx
import AgentWorkbench from './AgentWorkbench';
```

Add new state for AgentWorkbench:
```jsx
const [agentWorkbenchExpanded, setAgentWorkbenchExpanded] = useState(false);
const [agentEvents, setAgentEvents] = useState([]);
```

Add after messages-container div (before input-area):
```jsx
{agentWorkbenchExpanded && (
  <AgentWorkbench
    events={agentEvents}
    isExpanded={agentWorkbenchExpanded}
    onToggle={() => setAgentWorkbenchExpanded(false)}
  />
)}
```

- [ ] **Step 4: Add Agent Workbench toggle to message actions**

Add button in message bubble's action bar:
```jsx
<button
  className="message-action-btn"
  onClick={() => setAgentWorkbenchExpanded(!agentWorkbenchExpanded)}
>
  Agent Workbench {agentWorkbenchExpanded ? '▲' : '▼'}
</button>
```

- [ ] **Step 5: Commit Phase 1 Task 1**

```bash
git add frontend/src/components/AgentWorkbench.jsx frontend/src/components/Stage.jsx frontend/src/styles/App.css
git commit -m "feat(frontend): add AgentWorkbench component

- Create AgentWorkbench component with agent flow visualization
- Add styles for agent status icons (idle/running/success/error)
- Integrate into Stage with expand/collapse toggle
- Connect to SSE events from existing chat_stream

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Enhance Inspector Tabs (Add Memory Tab)

**Files:**
- Create: `frontend/src/components/MemoryTab.jsx`
- Modify: `frontend/src/components/Inspector.jsx:1-50`

- [ ] **Step 1: Create MemoryTab.jsx**

```jsx
// frontend/src/components/MemoryTab.jsx
import React, { useState, useEffect } from 'react';

const MemoryTab = ({ userId = 'default' }) => {
  const [preferences, setPreferences] = useState({});
  const [historyTrips, setHistoryTrips] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPreferences();
  }, [userId]);

  const loadPreferences = async () => {
    try {
      const response = await fetch(`/api/preference/${userId}`);
      if (response.ok) {
        const data = await response.json();
        setPreferences(data.preferences || {});
        setHistoryTrips(data.history_trips || []);
      }
    } catch (error) {
      console.error('Failed to load preferences:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddPreference = async (key, value) => {
    try {
      const response = await fetch(`/api/preference/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, value })
      });
      if (response.ok) {
        setPreferences(prev => ({ ...prev, [key]: value }));
      }
    } catch (error) {
      console.error('Failed to update preference:', error);
    }
  };

  const formatPreferenceValue = (key, value) => {
    if (key.includes('budget') || key.includes('range')) {
      return `¥${value}`;
    }
    return value;
  };

  const getPreferenceIcon = (key) => {
    if (key.includes('cuisine') || key.includes('food')) return '🍜';
    if (key.includes('budget')) return '💰';
    if (key.includes('style') || key.includes('prefer')) return '📌';
    if (key.includes('destination')) return '📍';
    return '•';
  };

  if (loading) {
    return (
      <div className="memory-tab-loading">
        <div className="loading-dots">
          <span></span><span></span><span></span>
        </div>
        <span>Loading memory...</span>
      </div>
    );
  }

  return (
    <div className="memory-tab">
      {/* Session Context */}
      <div className="memory-section">
        <div className="memory-section-header">
          <span className="section-icon">🟢</span>
          <span>Session Context</span>
        </div>
        <div className="memory-section-content">
          <div className="memory-item">
            <span className="memory-label">Active for</span>
            <span className="memory-value">23 messages</span>
          </div>
          <div className="memory-item">
            <span className="memory-label">Last:</span>
            <span className="memory-value">"帮我规划杭州3日游"</span>
          </div>
        </div>
      </div>

      {/* Long-term Memory */}
      <div className="memory-section">
        <div className="memory-section-header">
          <span className="section-icon">📌</span>
          <span>Key Preferences</span>
        </div>
        <div className="memory-section-content">
          {Object.entries(preferences).length === 0 ? (
            <div className="memory-empty">
              No preferences set yet
            </div>
          ) : (
            Object.entries(preferences).map(([key, value]) => (
              <div key={key} className="memory-preference-item">
                <span className="preference-icon">{getPreferenceIcon(key)}</span>
                <span className="preference-key">{key}:</span>
                <span className="preference-value">{formatPreferenceValue(key, value)}</span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Past Trips */}
      {historyTrips.length > 0 && (
        <div className="memory-section">
          <div className="memory-section-header">
            <span className="section-icon">📅</span>
            <span>Past Trips</span>
          </div>
          <div className="memory-section-content">
            {historyTrips.map((trip, index) => (
              <div key={index} className="memory-trip-item">
                <span className="trip-date">{trip.date}</span>
                <span className="trip-destination">{trip.destination}</span>
                <span className="trip-duration">{trip.duration}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="memory-actions">
        <button className="memory-action-btn" onClick={() => handleAddPreference('new_key', 'new_value')}>
          + Add Preference
        </button>
        <button className="memory-action-btn secondary">
          Edit Memory
        </button>
        <button className="memory-action-btn secondary">
          Export
        </button>
      </div>
    </div>
  );
};

export default MemoryTab;
```

- [ ] **Step 2: Add MemoryTab styles to App.css**

Add after `.inspector-content` styles:

```css
/* Memory Tab */
.memory-tab {
  padding: 16px;
}

.memory-tab-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  color: var(--text-muted);
  font-size: 12px;
}

.memory-section {
  margin-bottom: 16px;
}

.memory-section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.memory-section-content {
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  padding: 12px;
}

.memory-item {
  display: flex;
  gap: 8px;
  padding: 6px 0;
  font-size: 12px;
}

.memory-item:not(:last-child) {
  border-bottom: 1px solid var(--border-subtle);
}

.memory-label {
  color: var(--text-muted);
}

.memory-value {
  color: var(--text-primary);
  font-weight: 500;
}

.memory-empty {
  font-size: 12px;
  color: var(--text-muted);
  font-style: italic;
}

.memory-preference-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  font-size: 12px;
}

.memory-preference-item:not(:last-child) {
  border-bottom: 1px solid var(--border-subtle);
}

.preference-icon {
  font-size: 14px;
}

.preference-key {
  color: var(--text-secondary);
}

.preference-value {
  color: var(--text-primary);
  font-weight: 500;
}

.memory-trip-item {
  display: flex;
  gap: 8px;
  padding: 6px 0;
  font-size: 12px;
}

.memory-trip-item:not(:last-child) {
  border-bottom: 1px solid var(--border-subtle);
}

.trip-date {
  color: var(--text-muted);
}

.trip-destination {
  color: var(--text-primary);
  font-weight: 500;
}

.trip-duration {
  color: var(--text-secondary);
}

.memory-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
  flex-wrap: wrap;
}

.memory-action-btn {
  padding: 6px 12px;
  border-radius: var(--radius-md);
  font-size: 11px;
  font-weight: 500;
  background: var(--accent-primary);
  color: white;
  transition: all var(--transition-fast);
}

.memory-action-btn:hover {
  background: var(--accent-hover);
}

.memory-action-btn.secondary {
  background: var(--bg-secondary);
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
}

.memory-action-btn.secondary:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}
```

- [ ] **Step 3: Modify Inspector.jsx to support Memory tab**

Add new state for tabs:
```jsx
const [tabs, setTabs] = useState([
  { id: 'SOUL.md', label: 'SOUL', icon: '📜' },
  { id: 'IDENTITY.md', label: 'IDENTITY', icon: '👤' },
  { id: 'AGENTS.md', label: 'AGENTS', icon: '⚙️' },
  { id: 'Memory', label: 'Memory', icon: '🧠', isComponent: true },
]);
```

Modify the tab rendering to handle component tabs:
```jsx
{tab.id === 'Memory' ? (
  <MemoryTab userId="default" />
) : (
  <FileContent filename={tab.id} />
)}
```

- [ ] **Step 4: Import MemoryTab in Inspector.jsx**

Add at top of Inspector.jsx:
```jsx
import MemoryTab from './MemoryTab';
```

- [ ] **Step 5: Commit Phase 1 Task 2**

```bash
git add frontend/src/components/MemoryTab.jsx frontend/src/components/Inspector.jsx frontend/src/styles/App.css
git commit -m "feat(frontend): add Memory Tab to Inspector

- Create MemoryTab component with session context, preferences, past trips
- Fetch preferences from existing /api/preference/{user_id} endpoint
- Add Memory tab alongside SOUL.md, IDENTITY.md, AGENTS.md tabs
- Add corresponding styles

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Phase 2: Feature Cards & Quick Actions

### Task 3: Create FeatureCards Component

**Files:**
- Create: `frontend/src/components/FeatureCards.jsx`
- Modify: `frontend/src/components/Sidebar.jsx:1-50`

- [ ] **Step 1: Create FeatureCards.jsx**

```jsx
// frontend/src/components/FeatureCards.jsx
import React, { useState } from 'react';

const FEATURE_CARDS = [
  { id: 'attractions', icon: '🗺️', label: '景点推荐', status: 'coming_soon' },
  { id: 'route', icon: '📍', label: '路线规划', status: 'coming_soon' },
  { id: 'budget', icon: '💰', label: '预算控制', status: 'coming_soon' },
  { id: 'food', icon: '🍜', label: '美食推荐', status: 'coming_soon' },
  { id: 'hotel', icon: '🏨', label: '酒店预订', status: 'coming_soon' },
];

const FeatureCards = () => {
  const [isExpanded, setIsExpanded] = useState(true);

  const handleFeatureClick = (feature) => {
    if (feature.status === 'coming_soon') {
      // Future: Navigate to feature or show modal
      console.log(`Feature ${feature.id} clicked (coming soon)`);
    }
  };

  return (
    <div className="feature-cards">
      <div
        className="feature-cards-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="feature-cards-title">功能</span>
        <button className="feature-cards-toggle">
          {isExpanded ? '−' : '+'}
        </button>
      </div>

      {isExpanded && (
        <div className="feature-cards-list">
          {FEATURE_CARDS.map((feature) => (
            <div
              key={feature.id}
              className={`feature-card ${feature.status}`}
              onClick={() => handleFeatureClick(feature)}
            >
              <span className="feature-card-icon">
                {feature.status === 'coming_soon' ? '🔒' : feature.icon}
              </span>
              <span className="feature-card-label">{feature.label}</span>
              {feature.status === 'coming_soon' && (
                <span className="feature-card-badge">即将上线</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default FeatureCards;
```

- [ ] **Step 2: Add FeatureCards styles to App.css**

Add after `.section-action` styles:

```css
/* Feature Cards */
.feature-cards {
  border-top: 1px solid var(--border-subtle);
  padding-top: 8px;
  margin-top: 8px;
}

.feature-cards-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.feature-cards-header:hover {
  background: var(--bg-hover);
}

.feature-cards-title {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
}

.feature-cards-toggle {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 14px;
  transition: all var(--transition-fast);
}

.feature-cards-toggle:hover {
  background: var(--bg-active);
  color: var(--text-primary);
}

.feature-cards-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 8px 8px;
}

.feature-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.feature-card:hover {
  background: var(--bg-hover);
}

.feature-card.coming_soon {
  opacity: 0.6;
  cursor: default;
}

.feature-card.coming_soon:hover {
  background: transparent;
}

.feature-card-icon {
  font-size: 16px;
  width: 24px;
  text-align: center;
}

.feature-card-label {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.feature-card.coming_soon .feature-card-label {
  color: var(--text-muted);
}

.feature-card-badge {
  font-size: 9px;
  padding: 2px 6px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-weight: 500;
}
```

- [ ] **Step 3: Integrate FeatureCards into Sidebar.jsx**

Import and add to Sidebar:
```jsx
import FeatureCards from './FeatureCards';

// Add before session-list section in Sidebar JSX:
<FeatureCards />
```

- [ ] **Step 4: Commit Phase 2 Task 3**

```bash
git add frontend/src/components/FeatureCards.jsx frontend/src/components/Sidebar.jsx frontend/src/styles/App.css
git commit -m "feat(frontend): add Feature Cards to Sidebar

- Create FeatureCards component with 5 placeholder feature entries
- Features: attractions, route, budget, food, hotel
- All marked as coming_soon with lock icon
- Collapsible section with toggle

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 4: Enhance Input Area with Quick Action Chips

**Files:**
- Modify: `frontend/src/components/Stage.jsx` (InputArea section)

- [ ] **Step 1: Enhance InputArea in Stage.jsx**

Find the input-area section and add quick action chips after the textarea:

```jsx
{/* Quick Action Chips */}
<div className="input-quick-actions">
  <button className="quick-action-chip" title="Attach files">
    <span>📎</span>
    <span>文件</span>
  </button>
  <button className="quick-action-chip" title="Quick destination">
    <span>🎯</span>
    <span>目的地</span>
  </button>
  <button className="quick-action-chip disabled" title="Attraction picker (coming soon)" disabled>
    <span>📍</span>
    <span>景点</span>
  </button>
  <button className="quick-action-chip disabled" title="Budget input (coming soon)" disabled>
    <span>💰</span>
    <span>预算</span>
  </button>
</div>
```

- [ ] **Step 2: Add quick action styles to App.css**

Add after `.send-btn` styles:

```css
/* Quick Action Chips */
.input-quick-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.quick-action-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  font-size: 12px;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.quick-action-chip:hover:not(.disabled) {
  background: var(--bg-hover);
  border-color: var(--accent-primary);
  color: var(--text-primary);
}

.quick-action-chip.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.quick-action-chip span:first-child {
  font-size: 14px;
}
```

- [ ] **Step 3: Commit Phase 2 Task 4**

```bash
git add frontend/src/components/Stage.jsx frontend/src/styles/App.css
git commit -m "feat(frontend): add quick action chips to input area

- Add file attachment button
- Add destination quick input button
- Add disabled placeholder chips for attractions and budget
- Style with hover states for active buttons

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Phase 3: Enhanced Message Bubble

### Task 5: Add Action Bar to Message Bubble

**Files:**
- Modify: `frontend/src/components/Stage.jsx` (MessageBubble section)

- [ ] **Step 1: Add action bar to message bubble**

Find the message-meta section in the assistant message bubble and add:

```jsx
{/* Action Bar */}
<div className="message-action-bar">
  <button className="message-action-btn active">
    <span>💭</span>
    <span>Thinking</span>
  </button>
  <button className="message-action-btn">
    <span>🔧</span>
    <span>Tools</span>
  </button>
  <button
    className="message-action-btn"
    onClick={() => setAgentWorkbenchExpanded(!agentWorkbenchExpanded)}
  >
    <span>🤖</span>
    <span>Agent {agentWorkbenchExpanded ? '▲' : '▼'}</span>
  </button>
</div>
```

- [ ] **Step 2: Add message action bar styles to App.css**

Add after `.message-meta` styles:

```css
/* Message Action Bar */
.message-action-bar {
  display: flex;
  gap: 4px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}

.message-action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: var(--radius-md);
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  background: transparent;
  transition: all var(--transition-fast);
}

.message-action-btn:hover {
  background: var(--bg-hover);
  color: var(--text-secondary);
}

.message-action-btn.active {
  background: var(--accent-muted);
  color: var(--accent-primary);
}

.message-action-btn span:first-child {
  font-size: 12px;
}
```

- [ ] **Step 3: Commit Phase 3 Task 5**

```bash
git add frontend/src/components/Stage.jsx frontend/src/styles/App.css
git commit -m "feat(frontend): add action bar to message bubble

- Add Thinking, Tools, Agent Workbench action buttons
- Toggle agent workbench from message bubble
- Style with active state for current tab

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Phase 4: SSE Event Integration

### Task 6: Create useAgentEvents Hook

**Files:**
- Create: `frontend/src/hooks/useAgentEvents.js`
- Modify: `frontend/src/components/Stage.jsx:1-50`

- [ ] **Step 1: Create useAgentEvents.js**

```javascript
// frontend/src/hooks/useAgentEvents.js
import { useState, useEffect, useRef } from 'react';

const useAgentEvents = (sessionId) => {
  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);
  const eventSourceRef = useRef(null);

  useEffect(() => {
    if (!sessionId) return;

    // Note: The actual SSE connection is handled via EventSource in the chat component
    // This hook is a placeholder for future standalone agent event subscription
    // For now, events come through the chat_stream SSE connection

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [sessionId]);

  const addEvent = (event) => {
    setEvents(prev => [...prev, { ...event, timestamp: Date.now() }]);
  };

  const clearEvents = () => {
    setEvents([]);
  };

  return {
    events,
    connected,
    addEvent,
    clearEvents,
  };
};

export default useAgentEvents;
```

- [ ] **Step 2: Commit Phase 4 Task 6**

```bash
git add frontend/src/hooks/useAgentEvents.js
git commit -m "feat(frontend): add useAgentEvents hook

- Create hook for agent event management
- Placeholder for future standalone agent SSE subscription
- Provides addEvent and clearEvents helpers

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Final Integration

### Task 7: Final Integration and Testing

**Files:**
- Modify: `frontend/src/App.jsx:1-274`
- Modify: `frontend/src/styles/App.css`

- [ ] **Step 1: Review and finalize all imports in App.jsx**

Ensure all components are properly imported:
```jsx
import Sidebar from './components/Sidebar';
import Stage from './components/Stage';
import Inspector from './components/Inspector';
```

- [ ] **Step 2: Test the complete integration**

Manual testing checklist:
- [ ] Sidebar shows Feature Cards section
- [ ] Feature Cards are collapsible
- [ ] Feature Cards show 5 features with coming_soon status
- [ ] Inspector has Memory tab alongside SOUL.md, IDENTITY.md, AGENTS.md
- [ ] Memory tab fetches and displays preferences
- [ ] Agent Workbench toggle works in message bubble
- [ ] Input area shows quick action chips
- [ ] All styles apply correctly

- [ ] **Step 3: Commit final integration**

```bash
git add -A
git commit -m "feat(frontend): complete Agent UI redesign

Phase 1:
- AgentWorkbench component with agent flow visualization
- MemoryTab component in Inspector

Phase 2:
- FeatureCards in Sidebar with 5 coming_soon features

Phase 3:
- Enhanced message bubble with action bar
- Quick action chips in input area

Phase 4:
- useAgentEvents hook for future SSE integration

All components styled and integrated into existing three-panel layout.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Testing Instructions

### Manual Testing
1. Start the frontend dev server: `cd frontend && npm run dev`
2. Start the backend: `uvicorn app.main:app --reload`
3. Open browser to http://localhost:5173
4. Test each feature according to the checklist above

### Browser Console Checkpoints
- No React errors on page load
- No 404 errors for missing assets
- SSE connection establishes on chat start
- Preferences fetch successfully from `/api/preference/default`

---

## Rollback Plan

If issues occur:
```bash
# Rollback to before this feature
git revert HEAD
```

Or rollback specific phases:
```bash
# Rollback Phase 1 only
git revert <commit-hash-for-phase-1>

# Rollback Phase 2 only
git revert <commit-hash-for-phase-2>
```
