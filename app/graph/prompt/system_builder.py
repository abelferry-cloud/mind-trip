"""app/graph/prompt/system_builder.py — Layer 1: System Prompt 加载器。

读取 workspace/SYSTEM_PROMPT_<agent_name>.md 作为 Layer 1。
文件不存在时返回空字符串，不抛异常。
"""
import re
from pathlib import Path

from app.graph.prompt.config import WORKSPACE_DIR, SYSTEM_PROMPT_FILE


def _strip_frontmatter(content: str) -> str:
    """去除 Markdown 文件头的 YAML frontmatter (---...--- 块)。"""
    pattern = r'^---\s*\n.*?\n---\s*\n?'
    return re.sub(pattern, "", content, flags=re.DOTALL).strip()


class SystemPromptBuilder:
    """加载 Agent 的 SYSTEM_PROMPT_<name>.md 文件。

    文件不存在时返回空字符串，不抛异常。
    """

    def load(self, agent_name: str) -> str:
        filepath = WORKSPACE_DIR / SYSTEM_PROMPT_FILE.format(agent_name=agent_name)
        if not filepath.exists():
            return ""
        try:
            return _strip_frontmatter(filepath.read_text(encoding="utf-8"))
        except Exception:
            return ""
