import React, { useState, useEffect, useCallback } from 'react'
import markdownIt from 'markdown-it'

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
  const [files, setFiles] = useState([])
  const [currentModifiedAt, setCurrentModifiedAt] = useState(null)
  const POLL_INTERVAL = 3000

  const md = markdownIt({
    html: false,
    linkify: true,
    typographer: true
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
    // Load file content when file changes
    if (file) {
      loadFileContent(file)
    }
  }, [file, loadFileContent])

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
            <FileIcon fileName={f.name} isActive={file === f.name} />
            <span className="tab-label">{f.name}</span>
          </button>
        ))}
      </div>

      <div
        className="inspector-content"
        dangerouslySetInnerHTML={{ __html: md.render(content) }}
      />

      <div className="inspector-footer">
        <span>Markdown · UTF-8</span>
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

const FileIcon = ({ fileName, isActive }) => {
  const ext = fileName.split('.').pop()
  const color = isActive ? 'var(--orange)' : 'currentColor'
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 14, height: 14, flexShrink: 0 }}>
      {ext === 'md' ? (
        <>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
        </>
      ) : (
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      )}
    </svg>
  )
}

export default Inspector
