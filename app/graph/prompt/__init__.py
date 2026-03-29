"""app/graph/prompt — OpenClaw 三层动态提示词系统。

模块结构：
- config: 路径与文件常量
- system_builder: Layer 1 — System Prompt 加载
- workspace_loader: Layer 2 — Workspace 动态加载（LangChain Runnable）
- memory_loader: Layer 3 — Session Memory 加载
- composer: PromptComposer — 三层组合器（LangChain Runnable）
"""
from app.graph.prompt.config import (
    WORKSPACE_DIR,
    MEMORY_DIR,
    WORKSPACE_CORE_FILES,
    MAIN_SESSION_ONLY,
)
from app.graph.prompt.system_builder import SystemPromptBuilder
from app.graph.prompt.workspace_loader import WorkspaceLoader
from app.graph.prompt.memory_loader import MemoryLoader
from app.graph.prompt.composer import PromptComposer

__all__ = [
    "PromptComposer",
    "WorkspaceLoader",
    "MemoryLoader",
    "SystemPromptBuilder",
    "WORKSPACE_DIR",
    "MEMORY_DIR",
    "WORKSPACE_CORE_FILES",
    "MAIN_SESSION_ONLY",
]
