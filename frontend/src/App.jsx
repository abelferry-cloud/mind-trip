import React, { useState, useCallback, useEffect, useRef } from 'react'
import Sidebar from './components/Sidebar'
import Stage from './components/Stage'
import Inspector from './components/Inspector'
import { getSessionTitles, setSessionTitle, removeSessionTitle } from './utils/sessionStorage'
import './styles/App.css'

const App = () => {
  const [activeTab, setActiveTab] = useState('chat')
  const [sessions, setSessions] = useState([])
  const [currentSessionId, setCurrentSessionId] = useState(null)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [historyMessages, setHistoryMessages] = useState({})
  const [inspectorFile, setInspectorFile] = useState('SOUL.md')
  const [isLoading, setIsLoading] = useState(true)

  // Panel sizes
  const [sidebarWidth, setSidebarWidth] = useState(260)
  const [inspectorWidth, setInspectorWidth] = useState(380)
  const [inputHeight, setInputHeight] = useState(120)

  // Resize state
  const [resizing, setResizing] = useState(null)
  const containerRef = useRef(null)

  // 加载会话列表
  useEffect(() => {
    const loadSessions = async () => {
      try {
        const response = await fetch('/api/sessions')
        if (!response.ok) throw new Error('Failed to fetch sessions')
        const data = await response.json()

        const localTitles = getSessionTitles()
        const merged = data.map(session => ({
          id: session.session_id,
          session_id: session.session_id,
          title: localTitles[session.session_id] || `会话 ${session.session_id.slice(0, 6)}`,
          history_count: session.history_count,
          has_memory: session.has_memory,
          messages: []
        }))

        setSessions(merged)
        if (merged.length > 0 && !currentSessionId) {
          setCurrentSessionId(merged[0].id)
        }
      } catch (error) {
        console.error('Failed to load sessions:', error)
      } finally {
        setIsLoading(false)
      }
    }
    loadSessions()
  }, [])

  const currentSession = sessions.find(s => s.id === currentSessionId) || sessions[0] || null

  const handleNewSession = async () => {
    try {
      const response = await fetch('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      if (!response.ok) throw new Error('Failed to create session')
      const { session_id } = await response.json()

      const newSession = {
        id: session_id,
        session_id: session_id,
        title: '新会话',
        history_count: 0,
        has_memory: false,
        messages: []
      }

      setSessions(prev => [newSession, ...prev])
      setCurrentSessionId(session_id)
    } catch (error) {
      console.error('Failed to create session:', error)
    }
  }

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

  const handleDeleteSession = (sessionId) => {
    setSessions(prev => prev.filter(s => s.id !== sessionId))
    removeSessionTitle(sessionId)
    if (currentSessionId === sessionId) {
      const remaining = sessions.filter(s => s.id !== sessionId)
      setCurrentSessionId(remaining.length > 0 ? remaining[0].id : null)
    }
  }

  const handleRenameSession = (sessionId, newTitle) => {
    setSessions(prev => prev.map(s =>
      s.id === sessionId ? { ...s, title: newTitle } : s
    ))
    const session = sessions.find(s => s.id === sessionId)
    if (session) {
      setSessionTitle(session.session_id, newTitle)
    }
  }

  const handleUpdateMessage = (sessionId, newMessages) => {
    setSessions(prev => prev.map(s =>
      s.id === sessionId ? { ...s, messages: newMessages } : s
    ))
  }

  const handleUpdateSessionTitle = (sessionId, newTitle) => {
    setSessions(prev => prev.map(s =>
      s.id === sessionId ? { ...s, title: newTitle } : s
    ))
    const session = sessions.find(s => s.id === sessionId)
    if (session) {
      setSessionTitle(session.session_id, newTitle)
    }
  }

  // Resize handlers
  const handleResizeStart = useCallback((e, type) => {
    e.preventDefault()
    e.stopPropagation()
    setResizing(type)
  }, [])

  useEffect(() => {
    if (!resizing) return

    const handleMouseMove = (e) => {
      if (!containerRef.current) return
      const rect = containerRef.current.getBoundingClientRect()

      if (resizing === 'sidebar') {
        const newWidth = Math.max(180, Math.min(400, e.clientX - rect.left))
        setSidebarWidth(newWidth)
      } else if (resizing === 'inspector') {
        const newWidth = Math.max(280, Math.min(600, rect.right - e.clientX))
        setInspectorWidth(newWidth)
      } else if (resizing === 'input') {
        const newHeight = Math.max(80, Math.min(300, rect.bottom - e.clientY))
        setInputHeight(newHeight)
      }
    }

    const handleMouseUp = () => {
      setResizing(null)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [resizing])

  if (isLoading) {
    return (
      <div className="app-loading">
        <div className="loading-spinner"></div>
        <span>加载中...</span>
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      className={`app-container ${resizing ? 'resizing' : ''}`}
    >
      <Sidebar
        style={{ width: sidebarWidth }}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={handleSelectSession}
        onNewSession={handleNewSession}
        onDeleteSession={handleDeleteSession}
        onRenameSession={handleRenameSession}
      />

      {/* Sidebar Resize Handle */}
      <div
        className="resize-handle vertical"
        onMouseDown={(e) => handleResizeStart(e, 'sidebar')}
      />

      <Stage
        style={{ flex: 1 }}
        session={currentSession}
        onUpdateMessage={handleUpdateMessage}
        onUpdateSessionTitle={handleUpdateSessionTitle}
        inspectorFile={inspectorFile}
        onInspectorFileChange={setInspectorFile}
        inputHeight={inputHeight}
        onInputHeightChange={setInputHeight}
        onResizeStart={(e) => handleResizeStart(e, 'input')}
        resizing={resizing === 'input'}
        messages={historyMessages[currentSessionId] || []}
        loadingMessages={loadingMessages}
      />

      {/* Inspector Resize Handle */}
      <div
        className="resize-handle vertical"
        onMouseDown={(e) => handleResizeStart(e, 'inspector')}
      />

      <Inspector
        style={{ width: inspectorWidth }}
        file={inspectorFile}
        onFileChange={setInspectorFile}
      />
    </div>
  )
}

export default App
