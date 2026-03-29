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
    return FileContent(name=filename, content=content, modified_at=mtime.isoformat())


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