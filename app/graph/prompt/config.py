"""app/graph/prompt/config.py — Workspace 路径与文件常量。

参考 OpenClaw 的 workspace 文件布局：
- Layer 1: SYSTEM_PROMPT_<agent_name>.md
- Layer 2: SOUL.md / IDENTITY.md / USER.md / AGENTS.md / TOOLS.md / BOOTSTRAP.md
- Layer 2 (main only): MEMORY.md
- Layer 3: memory/YYYY-MM-DD.md
"""
from pathlib import Path

WORKSPACE_DIR = Path(__file__).parent.parent.parent / "workspace"

# Layer 1: System Prompt 文件命名模式
SYSTEM_PROMPT_FILE = "SYSTEM_PROMPT_{agent_name}.md"

# Layer 2: Workspace 核心文件（按加载顺序）
WORKSPACE_CORE_FILES = [
    "SOUL.md",
    "IDENTITY.md",
    "USER.md",
    "AGENTS.md",
    "TOOLS.md",
    "BOOTSTRAP.md",
]

# Layer 2: 仅主会话（main）加载
MAIN_SESSION_ONLY = ["MEMORY.md"]

# Layer 3: 每日 Memory 目录
MEMORY_DIR = WORKSPACE_DIR / "memory"
