"""app/graph/prompt/workspace_loader.py — Layer 2: Workspace 动态加载器。

LangChain Runnable — 每次 invoke 动态加载 Layer 2 文件。
遵循 OpenClaw 的上下文分层：
- SOUL / IDENTITY / USER / AGENTS / TOOLS / BOOTSTRAP 始终加载
- MEMORY.md 仅在 mode="main" 时注入
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from langchain_core.runnables import Runnable

from app.graph.prompt.config import WORKSPACE_DIR, WORKSPACE_CORE_FILES, MAIN_SESSION_ONLY


def _strip_frontmatter(content: str) -> str:
    pattern = r'^---\s*\n.*?\n---\s*\n?'
    return re.sub(pattern, "", content, flags=re.DOTALL).strip()


def _read_workspace_file(filename: str) -> Optional[str]:
    """读取 workspace 目录下的 .md 文件，返回剥离 frontmatter 后的内容。

    文件不存在或读取失败时返回 None。
    """
    filepath = WORKSPACE_DIR / filename
    if not filepath.exists():
        return None
    try:
        return _strip_frontmatter(filepath.read_text(encoding="utf-8"))
    except Exception:
        return None


def _section_block(title: str, content: str) -> str:
    """将内容包装为带标题的 Markdown 区块。"""
    return f"\n## {title}\n\n{content}\n"


class WorkspaceLoader(Runnable):
    """LangChain Runnable — 每次 invoke 动态加载 Layer 2 文件。"""

    def __init__(self, mode: Literal["main", "shared"] = "shared"):
        self.mode = mode

    def invoke(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """LangChain Runnable.invoke().

        Args:
            input: 支持 session_mode 覆盖初始化时的 mode

        Returns:
            {"workspace_prompt": str, "workspace_loaded_at": ISO datetime}
        """
        mode = input.get("session_mode", self.mode)
        file_order = WORKSPACE_CORE_FILES + (MAIN_SESSION_ONLY if mode == "main" else [])

        prompt_parts = []
        for filename in file_order:
            content = _read_workspace_file(filename)
            if content is None:
                continue
            section_name = filename.replace(".md", "")
            prompt_parts.append(_section_block(section_name, content))

        workspace_prompt = "\n".join(prompt_parts)
        return {
            "workspace_prompt": workspace_prompt,
            "workspace_loaded_at": datetime.now().isoformat(),
        }
