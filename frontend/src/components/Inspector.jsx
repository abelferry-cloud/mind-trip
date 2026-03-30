import React, { useState, useEffect, useCallback } from 'react'
import markdownIt from 'markdown-it'
import MemoryTab from './MemoryTab';

const ALLOWED_FILES = [
  'AGENTS.md',
  'BOOTSTRAP.md',
  'IDENTITY.md',
  'SOUL.md',
  'USER.md',
  'MEMORY.md'
]

const FILE_DESCRIPTIONS = {
  'SOUL.md': 'Core personality & principles',
  'IDENTITY.md': 'Agent identity template',
  'AGENTS.md': 'Multi-agent coordination rules',
  'USER.md': 'User context template',
  'MEMORY.md': 'Long-term memory storage',
  'BOOTSTRAP.md': 'Bootstrap configuration'
}

const Inspector = ({ file, onFileChange, style }) => {
  const [content, setContent] = useState('')
  const [files, setFiles] = useState([])
  const [currentModifiedAt, setCurrentModifiedAt] = useState(null)
  const [hoveredTab, setHoveredTab] = useState(null)
  const POLL_INTERVAL = 3000

  const md = markdownIt({
    html: false,
    linkify: true,
    typographer: true,
    breaks: true
  })

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
    } catch (error) {
      setContent('')
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
    if (file) {
      loadFileContent(file)
    }
  }, [file, loadFileContent])

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    if (isNaN(date.getTime())) return ''
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  }

  const currentFile = files.find(f => f.name === file)
  const description = FILE_DESCRIPTIONS[file] || ''

  return (
    <aside className="inspector" style={style}>
      {/* Header */}
      <div className="inspector-header">
        <div className="inspector-title">
          <div className="inspector-icon">
            {file === 'Memory' ? <BrainIcon /> : <CodeIcon />}
          </div>
          <div className="inspector-title-text">
            <span className="title-main">Inspector</span>
            <span className="title-sub">{file === 'Memory' ? 'Session Memory' : 'Workspace Files'}</span>
          </div>
        </div>
        <div className="inspector-actions">
          <button className="inspector-action-btn" title="Refresh">
            <RefreshIcon />
          </button>
        </div>
      </div>

      {/* Horizontal Tabs */}
      <div className="inspector-tab-bar">
        <div className="inspector-tabs">
          {files.map(f => (
            <button
              key={f.name}
              className={`inspector-tab ${file === f.name ? 'active' : ''} ${hoveredTab === f.name ? 'hovered' : ''}`}
              onClick={() => onFileChange(f.name)}
              onMouseEnter={() => setHoveredTab(f.name)}
              onMouseLeave={() => setHoveredTab(null)}
              title={FILE_DESCRIPTIONS[f.name] || f.name}
            >
              <span className="tab-icon">
                <MarkdownIcon />
              </span>
              <span className="tab-name">{f.name.replace('.md', '')}</span>
              <span className="tab-ext">.md</span>
            </button>
          ))}
          <button
            key="Memory"
            className={`inspector-tab ${file === 'Memory' ? 'active' : ''} ${hoveredTab === 'Memory' ? 'hovered' : ''}`}
            onClick={() => onFileChange('Memory')}
            onMouseEnter={() => setHoveredTab('Memory')}
            onMouseLeave={() => setHoveredTab(null)}
            title="Session memory & preferences"
          >
            <span className="tab-icon">
              <BrainIcon />
            </span>
            <span className="tab-name">Memory</span>
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div className="inspector-body">
        {file === 'Memory' ? (
          <MemoryTab userId="default" />
        ) : (
          <>
            {file && (
              <div className="inspector-content-header">
                <div className="content-file-info">
                  <div className="content-file-icon">
                    <LargeMarkdownIcon />
                  </div>
                  <div className="content-file-meta">
                    <span className="content-file-name">{file}</span>
                    <span className="content-file-desc">{description}</span>
                  </div>
                </div>
                {currentFile?.modified_at && (
                  <div className="content-modified">
                    <ClockIcon />
                    <span>{formatDate(currentFile.modified_at)}</span>
                  </div>
                )}
              </div>
            )}

            <div
              className="inspector-content"
              dangerouslySetInnerHTML={{ __html: md.render(content) }}
            />
          </>
        )}
      </div>

      {/* Footer */}
      <div className="inspector-footer">
        <div className="footer-left">
          {file === 'Memory' ? (
            <>
              <span className="footer-badge">Memory</span>
              <span className="footer-sep">·</span>
              <span className="footer-text">Session Data</span>
            </>
          ) : (
            <>
              <span className="footer-badge">Markdown</span>
              <span className="footer-sep">·</span>
              <span className="footer-text">UTF-8</span>
            </>
          )}
        </div>
        <div className="footer-right">
          <span className="footer-hint">Scroll to navigate</span>
        </div>
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

const RefreshIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M23 4v6h-6" />
    <path d="M1 20v-6h6" />
    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
  </svg>
)

const ClockIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <polyline points="12 6 12 12 16 14" />
  </svg>
)

const MarkdownIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
    <line x1="10" y1="9" x2="8" y2="9" />
  </svg>
)

const LargeMarkdownIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
    <line x1="10" y1="9" x2="8" y2="9" />
  </svg>
)

const BrainIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 4.5a2.5 2.5 0 0 0-4.96-.46 2.5 2.5 0 0 0-1.98 3 2.5 2.5 0 0 0-1.32 4.24 3 3 0 0 0 .34 5.58 2.5 2.5 0 0 0 2.96 3.08A2.5 2.5 0 0 0 12 19.5a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 12 4.5" />
    <path d="m15.7 10.4-.9.4" />
    <path d="m9.2 13.2-.9.4" />
    <path d="m13.6 15.7-.4-.9" />
    <path d="m10.8 9.2-.4-.9" />
    <path d="m15.7 13.5-.9-.4" />
    <path d="m9.2 10.9-.9-.4" />
    <path d="m10.4 15.7.4-.9" />
    <path d="m9.2 9.2.9-.4" />
  </svg>
)

export default Inspector
