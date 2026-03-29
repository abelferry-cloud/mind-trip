import React, { useState, useEffect, useCallback } from 'react'
import Editor from '@monaco-editor/react'

const ALLOWED_FILES = [
  'AGENTS.md',
  'BOOTSTRAP.md',
  'IDENTITY.md',
  'SOUL.md',
  'USER.md',
  'MEMORY.md'
]

const Inspector = ({ file, onFileChange, style }) => {
  const [content, setContent] = useState('')
  const [isModified, setIsModified] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [files, setFiles] = useState([])
  const [currentModifiedAt, setCurrentModifiedAt] = useState(null)
  const POLL_INTERVAL = 3000

  const loadFileContent = useCallback(async (fileName) => {
    try {
      const response = await fetch(`/api/workspace/files/${fileName}`)
      if (response.ok) {
        const data = await response.json()
        setContent(data.content)
        setCurrentModifiedAt(data.modified_at)
      } else {
        setContent('')
      }
      setIsModified(false)
    } catch (error) {
      setContent('')
      setIsModified(false)
    }
  }, [])

  useEffect(() => {
    const loadFiles = async () => {
      try {
        const res = await fetch('/api/workspace/files')
        if (res.ok) {
          const data = await res.json()
          setFiles(data.filter(f => ALLOWED_FILES.includes(f.name)))
        }
      } catch (e) { /* ignore */ }
    }
    loadFiles()
  }, [])

  useEffect(() => {
    if (!file) return
    const interval = setInterval(async () => {
      try {
        const res = await fetch('/api/workspace/files')
        if (res.ok) {
          const data = await res.json()
          setFiles(data.filter(f => ALLOWED_FILES.includes(f.name)))
          const f = data.find(x => x.name === file)
          if (f && currentModifiedAt && f.modified_at !== currentModifiedAt) {
            loadFileContent(file)
          }
        }
      } catch (e) { /* ignore */ }
    }, POLL_INTERVAL)
    return () => clearInterval(interval)
  }, [file, currentModifiedAt, loadFileContent])

  useEffect(() => {
    // Load file content when file changes
    if (file) {
      loadFileContent(file)
    }
  }, [file, loadFileContent])

  const handleEditorChange = (value) => {
    setContent(value)
    setIsModified(true)
  }

  const handleSave = async () => {
    setIsSaving(true)
    try {
      const res = await fetch(`/api/workspace/files/${file}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: file, content, modified_at: currentModifiedAt })
      })
      if (res.ok) {
        const data = await res.json()
        setCurrentModifiedAt(data.modified_at)
        setIsModified(false)
      }
    } catch (error) {
      console.error('Failed to save:', error)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <aside className="inspector" style={style}>
      <div className="inspector-header">
        <div className="inspector-title">
          <CodeIcon />
          <span>Inspector</span>
        </div>
      </div>

      <div className="inspector-tabs">
        {files.map(f => (
          <button
            key={f.name}
            className={`inspector-tab ${file === f.name ? 'active' : ''}`}
            onClick={() => onFileChange(f.name)}
            title={f.name}
          >
            {f.name}
          </button>
        ))}
      </div>

      <div className="inspector-content">
        <Editor
          height="100%"
          language="markdown"
          theme="vs"
          value={content}
          onChange={handleEditorChange}
          options={{
            minimap: { enabled: false },
            fontSize: 13,
            fontFamily: 'JetBrains Mono, Fira Code, monospace',
            lineNumbers: 'on',
            wordWrap: 'on',
            scrollBeyondLastLine: false,
            automaticLayout: true,
            padding: { top: 12 },
            renderLineHighlight: 'line',
            cursorBlinking: 'smooth',
            smoothScrolling: true,
          }}
        />
      </div>

      <div className="inspector-footer">
        <div className="inspector-status">
          {isModified ? (
            <>
              <DotIcon style={{ color: 'var(--warning)' }} />
              <span>已修改</span>
            </>
          ) : (
            <>
              <DotIcon style={{ color: 'var(--success)' }} />
              <span>已同步</span>
            </>
          )}
        </div>
        <button
          className="stage-action-btn"
          onClick={handleSave}
          disabled={!isModified || isSaving}
          style={{ opacity: isModified ? 1 : 0.5 }}
        >
          {isSaving ? '保存中...' : '保存'}
        </button>
      </div>
    </aside>
  )
}

const CodeIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="16 18 22 12 16 6" />
    <polyline points="8 6 2 12 8 18" />
  </svg>
)

const DotIcon = ({ style }) => (
  <span style={{ ...style, width: 6, height: 6, borderRadius: '50%', display: 'inline-block' }} />
)

const PanelLeftCloseIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
    <line x1="9" y1="3" x2="9" y2="21" />
    <polyline points="15 8 10 12 15 16" />
  </svg>
)

export default Inspector
