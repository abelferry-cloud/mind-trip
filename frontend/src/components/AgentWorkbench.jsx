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
          setCurrentStep(`${event.agent || event.tool}: Starting...`);
          break;
        case 'tool_end':
          setCurrentStep(`${event.tool}: Completed in ${event.duration_ms}ms`);
          break;
        case 'reasoning_step':
          setCurrentStep(event.step);
          break;
        case 'llm_end':
          // Mark all running agents as success using functional setState
          setAgents(prev => {
            const updated = { ...prev };
            Object.keys(updated).forEach(key => {
              if (updated[key].status === 'running') {
                updated[key] = { ...updated[key], status: 'success' };
              }
            });
            return updated;
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