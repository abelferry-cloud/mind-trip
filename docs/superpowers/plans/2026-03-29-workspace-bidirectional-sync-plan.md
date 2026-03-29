# Workspace 双向同步实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现前端 Inspector 组件与后端 `app/workspace/` 目录的双向文件同步

**Architecture:** 后端新增 `/api/workspace/` 路由提供文件 CRUD，前端 Inspector 改为动态加载文件列表 + 轮询检测后端变更 + PUT 保存

**Tech Stack:** FastAPI (Python), React + Monaco Editor, 轮询同步

---

## Part 1: 后端 API

### Task 1: 创建 workspace API 路由

**Files:**
- Create: `app/api/workspace.py`
- Modify: `app/main.py` (import + register router — find existing import line and add `workspace`)

- [ ] **Step 1: 创建 app/api/workspace.py**

```python
# app/api/workspace.py
"""Workspace 文件管理 API。"""
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/api/workspace", tags=["workspace"])

WORKSPACE_DIR = Path(__file__).parent.parent / "workspace"


class FileInfo(BaseModel):
    name: str
    modified_at: datetime


class FileContent(BaseModel):
    name: str
    content: str
    modified_at: datetime


@router.get("/files", response_model=List[FileInfo])
async def list_workspace_files():
    """列出 workspace 目录下所有 .md 文件。"""
    if not WORKSPACE_DIR.exists():
        return []
    files = []
    for f in sorted(WORKSPACE_DIR.glob("*.md")):
        if f.name.startswith("."):
            continue
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=None)
        files.append(FileInfo(name=f.name, modified_at=mtime))
    return files


@router.get("/files/{filename}", response_model=FileContent)
async def get_workspace_file(filename: str):
    """读取指定文件内容。"""
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    file_path = WORKSPACE_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    content = file_path.read_text(encoding="utf-8")
    mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=None)
    return FileContent(name=filename, content=content, modified_at=mtime)


@router.put("/files/{filename}")
async def save_workspace_file(filename: str, body: FileContent):
    """保存文件内容。"""
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="Only .md files allowed")
    file_path = WORKSPACE_DIR / filename
    file_path.write_text(body.content, encoding="utf-8")
    mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=None)
    return {"name": filename, "modified_at": mtime.isoformat()}
```

- [ ] **Step 2: 修改 app/main.py，注册路由**

在 `app/main.py:9` 末尾添加 `workspace` import：
```python
from app.api import chat, plan, preference, monitor, session, workspace
```

在 `app/main.py:51` 后添加：
```python
    app.include_router(workspace.router)
```

- [ ] **Step 3: 测试 API 可用**

Run: `cd /d/pychram-workspace/smartJournal && python -m uvicorn app.main:app --reload --port 8000`
验证：
- `GET /api/workspace/files` 返回文件列表
- `GET /api/workspace/files/SOUL.md` 返回内容
- `PUT /api/workspace/files/SOUL.md` + `{ "name": "SOUL.md", "content": "test" }` 可保存

- [ ] **Step 4: Commit**

```bash
git add app/api/workspace.py app/main.py
git commit -m "feat(api): add /api/workspace CRUD endpoints for workspace files

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

---

## Part 2: 前端 Inspector 改造

### Task 2: Inspector 组件重构

**Files:**
- Modify: `frontend/src/components/Inspector.jsx` (complete rewrite of data fetching logic)

- [ ] **Step 1: 添加状态和轮询逻辑**

在 `Inspector` 组件中添加：
```javascript
const [files, setFiles] = useState([])        // 动态文件列表
const [currentModifiedAt, setCurrentModifiedAt] = useState(null)
const POLL_INTERVAL = 3000  // 3秒轮询
```

- [ ] **Step 2: 加载文件列表 useEffect**

```javascript
useEffect(() => {
  const loadFiles = async () => {
    try {
      const res = await fetch('/api/workspace/files')
      if (res.ok) {
        const data = await res.json()
        setFiles(data)
      }
    } catch (e) { /* ignore */ }
  }
  loadFiles()
}, [])
```

- [ ] **Step 3: 轮询检测后端变更 useEffect**

```javascript
useEffect(() => {
  if (!file) return
  const interval = setInterval(async () => {
    try {
      const res = await fetch('/api/workspace/files')
      if (res.ok) {
        const data = await res.json()
        setFiles(data)  // setFiles is stable from useState, no deps needed
        const f = data.find(x => x.name === file)
        if (f && currentModifiedAt && f.modified_at !== currentModifiedAt) {
          loadFileContent(file)  // 重新加载
        }
      }
    } catch (e) { /* ignore */ }
  }, POLL_INTERVAL)
  return () => clearInterval(interval)
}, [file, currentModifiedAt, loadFileContent])
```

> **Note:** `loadFileContent` must be wrapped in `useCallback` (see Step 4) so it can be a dependency here.

- [ ] **Step 4: 修改 loadFileContent 使用真实 API（useCallback 包装）**

```javascript
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
```

- [ ] **Step 5: 修改 handleSave 使用 PUT**

```javascript
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
```

- [ ] **Step 6: 移除硬编码 files 数组，改为动态渲染**

```javascript
// 移除硬编码：
// const files = [
//   { id: 'SOUL.md', path: '/workspace/SOUL.md' },
//   ...
// ]

// 改为动态渲染 tabs：
{files.map(f => (
  <button
    key={f.name}
    className={`inspector-tab ${file === f.name ? 'active' : ''}`}
    onClick={() => onFileChange(f.name)}
  >
    {f.name}
  </button>
))}
```

- [ ] **Step 7: 测试前后端连通**

1. 刷新前端页面
2. Inspector tabs 应显示 workspace 真实文件列表
3. 编辑文件内容，点击保存
4. 用编辑器直接修改 `app/workspace/SOUL.md`
5. 等待 3-5 秒，前端应自动刷新显示新内容

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/Inspector.jsx
git commit -m "feat(frontend): refactor Inspector for dynamic workspace file loading

- Load file list from /api/workspace/files
- Poll for backend changes every 3 seconds
- PUT save to /api/workspace/files/{filename}
- Remove hardcoded file list

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```
