import React, { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'

import { setSessionTitle } from '../utils/sessionStorage'

const Stage = ({
  session,
  messages,
  loadingMessages,
  onUpdateMessage,
  onUpdateSessionTitle,
  inspectorFile,
  onInspectorFileChange,
  inputHeight,
  onResizeStart,
  resizing,
  style,
  onToggleSidebar,
  sidebarVisible,
  onToggleInspector,
  inspectorVisible
}) => {
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [expandedThoughts, setExpandedThoughts] = useState({})
  const [streamingMsgId, setStreamingMsgId] = useState(null)
  const eventSourceRef = useRef(null)
  const typewriterRef = useRef(null)
  const messagesEndRef = useRef(null)
  const messagesRef = useRef([])

  // Typewriter animation: smoothly transfer contentBuffer to content
  useEffect(() => {
    const streamingMsgs = messages.filter(m => m.streaming && m.contentBuffer && m.contentBuffer !== m.content)
    if (streamingMsgs.length === 0) return

    const interval = setInterval(() => {
      onUpdateMessage(session.id, messages.map(msg => {
        if (msg.streaming && msg.contentBuffer && msg.contentBuffer !== msg.content) {
          return { ...msg, content: msg.contentBuffer }
        }
        return msg
      }))
    }, 50)

    return () => clearInterval(interval)
  }, [messages, session?.id])

  // Keep messagesRef in sync with displayMessages
  useEffect(() => {
    messagesRef.current = displayMessages
  }, [displayMessages])

  const displayMessages = messages.length > 0 ? messages : (session?.messages || [])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [displayMessages])

  // Streaming message creation
  const createStreamingMessage = (sessionId) => {
    return {
      id: `temp_${Date.now()}`,
      role: 'assistant',
      content: '',
      streaming: true,
      status: 'streaming',
      agent: 'PlanningAgent',
      model: '',
      iteration: 0,
      max_iterations: 10,
      toolCalls: [],
      tokenUsage: null,
      reasoningSteps: [],
      contentBuffer: '',
      error: null,
    }
  }

  // EventSource connection for streaming
  const startStreaming = (sessionId, messageId) => {
    const es = new EventSource(`/api/chat/stream?session_id=${sessionId}`)
    eventSourceRef.current = es

    es.addEventListener('connected', () => {
      console.log('SSE connected')
    })

    es.addEventListener('llm_start', (e) => {
      const { model } = JSON.parse(e.data)
      const updated = messagesRef.current.map(msg =>
        msg.id === messageId
          ? { ...msg, model }
          : msg
      )
      onUpdateMessage(sessionId, updated)
    })

    es.addEventListener('llm_end', (e) => {
      const usage = JSON.parse(e.data)
      const updated = messagesRef.current.map(msg =>
        msg.id === messageId
          ? { ...msg, tokenUsage: usage }
          : msg
      )
      onUpdateMessage(sessionId, updated)
    })

    es.addEventListener('model_switch', (e) => {
      const { model } = JSON.parse(e.data)
      const updated = messagesRef.current.map(msg =>
        msg.id === messageId
          ? { ...msg, model }
          : msg
      )
      onUpdateMessage(sessionId, updated)
    })

    es.addEventListener('ping', () => {})  // No-op per spec

    es.addEventListener('llm_new_token', (e) => {
      const { token } = JSON.parse(e.data)
      const updated = messagesRef.current.map(msg =>
        msg.id === messageId
          ? { ...msg, contentBuffer: (msg.contentBuffer || '') + token }
          : msg
      )
      onUpdateMessage(sessionId, updated)
    })

    es.addEventListener('tool_start', (e) => {
      const { tool, tool_call_id } = JSON.parse(e.data)
      const updated = messagesRef.current.map(msg =>
        msg.id === messageId
          ? {
              ...msg,
              toolCalls: [...msg.toolCalls, { tool, tool_call_id, status: 'running' }]
            }
          : msg
      )
      onUpdateMessage(sessionId, updated)
    })

    es.addEventListener('tool_end', (e) => {
      const { tool, summary, duration_ms } = JSON.parse(e.data)
      const updated = messagesRef.current.map(msg =>
        msg.id === messageId
          ? {
              ...msg,
              toolCalls: msg.toolCalls.map(tc =>
                tc.tool === tool
                  ? { ...tc, status: 'done', summary, duration_ms }
                  : tc
              )
            }
          : msg
      )
      onUpdateMessage(sessionId, updated)
    })

    es.addEventListener('token_usage', (e) => {
      const usage = JSON.parse(e.data)
      const updated = messagesRef.current.map(msg =>
        msg.id === messageId
          ? { ...msg, tokenUsage: usage }
          : msg
      )
      onUpdateMessage(sessionId, updated)
    })

    es.addEventListener('reasoning_step', (e) => {
      const { step } = JSON.parse(e.data)
      const updated = messagesRef.current.map(msg =>
        msg.id === messageId
          ? { ...msg, reasoningSteps: [...msg.reasoningSteps, step] }
          : msg
      )
      onUpdateMessage(sessionId, updated)
    })

    es.addEventListener('iteration', (e) => {
      const { iteration, max_iterations } = JSON.parse(e.data)
      const updated = messagesRef.current.map(msg =>
        msg.id === messageId
          ? { ...msg, iteration, max_iterations }
          : msg
      )
      onUpdateMessage(sessionId, updated)
    })

    es.addEventListener('agent_switch', (e) => {
      const { agent } = JSON.parse(e.data)
      const updated = messagesRef.current.map(msg =>
        msg.id === messageId
          ? { ...msg, agent }
          : msg
      )
      onUpdateMessage(sessionId, updated)
    })

    es.addEventListener('final', (e) => {
      const { answer } = JSON.parse(e.data)
      const updated = messagesRef.current.map(msg =>
        msg.id === messageId
          ? { ...msg, content: answer, streaming: false, status: 'done' }
          : msg
      )
      onUpdateMessage(sessionId, updated)
      es.close()
    })

    es.addEventListener('error', (e) => {
      const { error } = JSON.parse(e.data)
      const updated = messagesRef.current.map(msg =>
        msg.id === messageId
          ? { ...msg, error, streaming: false, status: 'error' }
          : msg
      )
      onUpdateMessage(sessionId, updated)
      es.close()
    })
  }

  // Retry streaming for a specific message
  const retryStream = (msgId) => {
    const msg = messages.find(m => m.id === msgId)
    if (msg && session) {
      // Close existing connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
      // Reset message state
      const updated = messages.map(m =>
        m.id === msgId
          ? { ...m, content: '', contentBuffer: '', streaming: true, status: 'streaming', error: null }
          : m
      )
      onUpdateMessage(session.id, updated)
      // Restart streaming
      startStreaming(session.id, msgId)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim() || isLoading || !session) return

    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString()
    }

    // 如果是首条用户消息，更新会话标题
    if (displayMessages.length === 0) {
      const title = input.trim().slice(0, 50)
      setSessionTitle(session.id, title)
      onUpdateSessionTitle(session.id, title)
    }

    // Create streaming message
    const assistantMessage = createStreamingMessage(session.id)
    setStreamingMsgId(assistantMessage.id)

    const newMessages = [...session.messages, userMessage, assistantMessage]
    onUpdateMessage(session.id, newMessages)
    setInput('')
    setIsLoading(true)

    // Start SSE connection
    startStreaming(session.id, assistantMessage.id)

    try {
      // Send to API (non-blocking for streaming)
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: 'default_user',
          session_id: session.id,
          message: input.trim()
        }),
      })

      if (!response.ok) {
        throw new Error('Stream failed')
      }
      // Response body is consumed by EventSource
    } catch (error) {
      // Handle error
      const updated = messagesRef.current.map(msg =>
        msg.id === assistantMessage.id
          ? { ...msg, content: '连接失败', streaming: false, status: 'error' }
          : msg
      )
      onUpdateMessage(session.id, updated)
    } finally {
      setIsLoading(false)
    }
  }

  // Mock thoughts for visualization
  const generateMockThoughts = (answer) => {
    if (!answer) return []
    return [
      { agent: 'PlanningAgent', thought: '解析用户意图：旅行目的地、天数、预算和偏好' },
      { agent: 'PreferenceAgent', thought: '查询用户历史偏好：倾向于深度体验而非打卡式旅游' },
      { agent: 'AttractionsAgent', thought: '根据目的地筛选热门景点，优先考虑小众目的地' },
      { agent: 'BudgetAgent', thought: '计算每日预算分配：住宿40%、餐饮25%、交通15%、门票20%' },
      { agent: 'RouteAgent', thought: '规划最优路线顺序，减少往返浪费时间' },
      { agent: 'FoodAgent', thought: '结合用户口味偏好推荐当地特色美食' },
      { agent: 'FinalAgent', thought: '整合所有子代理结果，生成完整行程规划' },
    ]
  }

  const toggleThoughts = (messageId) => {
    setExpandedThoughts(prev => ({
      ...prev,
      [messageId]: !prev[messageId]
    }))
  }

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <main className="stage" style={style}>
      <header className="stage-header">
        <div className="stage-header-left">
          <button
            className="stage-action-btn"
            onClick={onToggleSidebar}
            title={sidebarVisible ? '隐藏左侧菜单' : '显示左侧菜单'}
          >
            {sidebarVisible ? <PanelLeftCloseIcon /> : <PanelLeftOpenIcon />}
          </button>
          <div className="stage-title">
            <span>{session?.title || '新会话'}</span>
            <div className="stage-status">
              <span className={`status-dot ${isLoading ? '' : 'idle'}`}></span>
              <span>{isLoading ? '思考中...' : '就绪'}</span>
            </div>
          </div>
        </div>
        <div className="stage-header-right">
          <button
            className="stage-action-btn"
            onClick={() => onInspectorFileChange(inspectorFile === 'SOUL.md' ? 'MEMORY.md' : 'SOUL.md')}
          >
            <FileIcon />
            <span>{inspectorFile}</span>
          </button>
          <button
            className="stage-action-btn"
            onClick={onToggleInspector}
            title={inspectorVisible ? '隐藏右侧面板' : '显示右侧面板'}
          >
            {inspectorVisible ? <PanelRightCloseIcon /> : <PanelRightOpenIcon />}
          </button>
        </div>
      </header>

      <div className="messages-container">
        {loadingMessages && (
          <div className="loading-history">
            <div className="loading-spinner small"></div>
            <span>加载历史消息...</span>
          </div>
        )}

        {displayMessages.length === 0 ? (
          <div className="empty-state">
            <ChatEmptyIcon />
            <h3>开始新对话</h3>
            <p>输入你的旅行需求，AI 将为你规划完美行程</p>
          </div>
        ) : (
          displayMessages.map(message => (
            <div key={message.id} className={`message ${message.role}`}>
              <div className="message-avatar">
                {message.role === 'assistant' ? <BotIcon /> : <UserIcon />}
              </div>
              <div className="message-content">
                <div className="message-bubble">
                  <ReactMarkdown>{message.contentBuffer || message.content}</ReactMarkdown>

                  {message.streaming && (
                    <div className="streaming-status-panel">
                      <div className="streaming-header">
                        <span className="agent-name">🤖 {message.agent}</span>
                        {message.model && <span className="model-name">via {message.model}</span>}
                      </div>

                      {message.toolCalls.length > 0 && (
                        <div className="tool-calls">
                          {message.toolCalls.map((tc, i) => (
                            <div key={i} className={`tool-call ${tc.status}`}>
                              <span className="tool-icon">
                                {tc.status === 'running' ? '🔧' : tc.status === 'done' ? '✅' : '❌'}
                              </span>
                              <span className="tool-name">{tc.tool}</span>
                              {tc.status === 'done' && tc.summary && (
                                <span className="tool-summary">→ {tc.summary}</span>
                              )}
                              {tc.status === 'done' && tc.duration_ms && (
                                <span className="tool-duration">({tc.duration_ms}ms)</span>
                              )}
                            </div>
                          ))}
                        </div>
                      )}

                      {message.tokenUsage && (
                        <div className="token-usage">
                          📊 Token: {message.tokenUsage.prompt_tokens} / {message.tokenUsage.completion_tokens} / {message.tokenUsage.total_tokens}
                          {message.tokenUsage.cost_usd && ` ($${message.tokenUsage.cost_usd})`}
                        </div>
                      )}

                      {message.reasoningSteps.length > 0 && (
                        <div className="reasoning-steps">
                          {message.reasoningSteps.map((step, i) => (
                            <div key={i} className="reasoning-step">💭 {step}</div>
                          ))}
                        </div>
                      )}

                      {message.error && (
                        <div className="stream-error">
                          ⚠️ {message.error}
                          <button onClick={() => retryStream(message.id)}>重新发送</button>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {message.role === 'assistant' && message.thoughts && message.thoughts.length > 0 && (
                  <>
                    <div className="message-meta">
                      <button
                        className={`thoughts-toggle ${expandedThoughts[message.id] ? 'expanded' : ''}`}
                        onClick={() => toggleThoughts(message.id)}
                      >
                        <ChevronIcon />
                        <span>思考链 ({message.thoughts.length} 步)</span>
                      </button>
                    </div>

                    {expandedThoughts[message.id] && (
                      <div className="thoughts-chain">
                        {message.thoughts.map((thought, index) => (
                          <div key={index} className="thought-step">
                            <ThoughtIcon className="thought-icon" />
                            <div className="thought-text">
                              <strong>{thought.agent}:</strong> {thought.thought}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )}

                <div className="message-meta">
                  <span>{formatTime(message.timestamp)}</span>
                  {message.modelUsed && (
                    <span>via {message.modelUsed}</span>
                  )}
                </div>
              </div>
            </div>
          ))
        )}

        {isLoading && (
          <div className="message assistant">
            <div className="message-avatar">
              <BotIcon />
            </div>
            <div className="message-content">
              <div className="message-bubble">
                <div className="loading-indicator">
                  <div className="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                  <span>正在思考...</span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Resize Handle */}
      <div
        className={`resize-handle horizontal ${resizing ? 'active' : ''}`}
        onMouseDown={onResizeStart}
      />

      <form className="input-area" onSubmit={handleSubmit}>
        <div
          className="input-wrapper"
          style={{ height: inputHeight, alignItems: 'stretch' }}
        >
          <textarea
            className="message-input"
            placeholder="描述你的旅行需求..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSubmit(e)
              }
            }}
          />
          <button type="submit" className="send-btn" disabled={!input.trim() || isLoading}>
            <SendIcon />
          </button>
        </div>
      </form>
    </main>
  )
}

// Icons
const BotIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2z" />
    <circle cx="7.5" cy="14.5" r="1.5" />
    <circle cx="16.5" cy="14.5" r="1.5" />
  </svg>
)

const UserIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
)

const SendIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13" />
    <polygon points="22 2 15 22 11 13 2 9 22 2" />
  </svg>
)

const ChevronIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="9 18 15 12 9 6" />
  </svg>
)

const ThoughtIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
)

const FileIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
    <polyline points="10 9 9 9 8 9" />
  </svg>
)

const PanelLeftCloseIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
    <line x1="9" y1="3" x2="9" y2="21" />
    <polyline points="15 16 11 12 15 8" />
  </svg>
)

const PanelLeftOpenIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
    <line x1="9" y1="3" x2="9" y2="21" />
    <polyline points="9 8 14 12 9 16" />
  </svg>
)

const PanelRightCloseIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
    <line x1="15" y1="3" x2="15" y2="21" />
    <polyline points="9 16 13 12 9 8" />
  </svg>
)

const PanelRightOpenIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
    <line x1="15" y1="3" x2="15" y2="21" />
    <polyline points="15 8 10 12 15 16" />
  </svg>
)

const ChatEmptyIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    <line x1="9" y1="10" x2="15" y2="10" />
  </svg>
)

export default Stage
