import React, { useState } from 'react'

const Sidebar = ({
  activeTab,
  onTabChange,
  sessions,
  currentSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  onRenameSession,
  style
}) => {
  const [editingId, setEditingId] = useState(null)
  const [editTitle, setEditTitle] = useState('')

  const handleStartEdit = (session, e) => {
    e.stopPropagation()
    setEditingId(session.id)
    setEditTitle(session.title)
  }

  const handleSaveEdit = (sessionId) => {
    if (editTitle.trim()) {
      onRenameSession(sessionId, editTitle.trim())
    }
    setEditingId(null)
  }

  const handleKeyDown = (e, sessionId) => {
    if (e.key === 'Enter') {
      handleSaveEdit(sessionId)
    } else if (e.key === 'Escape') {
      setEditingId(null)
    }
  }

  const navItems = [
    { id: 'chat', label: '对话', icon: ChatIcon },
    { id: 'memory', label: '记忆', icon: MemoryIcon },
    { id: 'skills', label: '技能', icon: SkillsIcon },
  ]

  return (
    <aside className="sidebar" style={style}>
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <LogoIcon />
          <span>SmartJourney</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map(item => (
          <button
            key={item.id}
            className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
            onClick={() => onTabChange(item.id)}
          >
            <item.icon />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-section">
        <div className="section-header">
          <span className="section-title">会话列表</span>
          <button className="section-action" onClick={onNewSession} title="新建会话">
            <PlusIcon />
          </button>
        </div>
      </div>

      <div className="session-list">
        {sessions.map(session => (
          <div
            key={session.id}
            className={`session-item ${session.id === currentSessionId ? 'active' : ''}`}
            onClick={() => onSelectSession(session.id)}
          >
            {editingId === session.id ? (
              <input
                type="text"
                className="session-input"
                value={editTitle}
                onChange={e => setEditTitle(e.target.value)}
                onBlur={() => handleSaveEdit(session.id)}
                onKeyDown={e => handleKeyDown(e, session.id)}
                autoFocus
                onClick={e => e.stopPropagation()}
              />
            ) : (
              <>
                <div className="session-title">{session.title}</div>
                <div className="session-meta">
                  {session.history_count > 0 && (
                    <span className="meta-badge">{session.history_count} 条</span>
                  )}
                  {session.has_memory && (
                    <span className="meta-badge memory">记忆</span>
                  )}
                </div>
                <div className="session-actions">
                  <button
                    className="session-action-btn"
                    onClick={e => handleStartEdit(session, e)}
                    title="重命名"
                  >
                    <EditIcon />
                  </button>
                  <button
                    className="session-action-btn delete"
                    onClick={e => {
                      e.stopPropagation()
                      onDeleteSession(session.id)
                    }}
                    title="删除"
                  >
                    <TrashIcon />
                  </button>
                </div>
              </>
            )}
          </div>
        ))}
      </div>
    </aside>
  )
}

// Icons
const LogoIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2L2 7l10 5 10-5-10-5z" />
    <path d="M2 17l10 5 10-5" />
    <path d="M2 12l10 5 10-5" />
  </svg>
)

const ChatIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  </svg>
)

const MemoryIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
  </svg>
)

const SkillsIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
  </svg>
)

const PlusIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="5" x2="12" y2="19" />
    <line x1="5" y1="12" x2="19" y2="12" />
  </svg>
)

const EditIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
  </svg>
)

const TrashIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6" />
    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
  </svg>
)

export default Sidebar
