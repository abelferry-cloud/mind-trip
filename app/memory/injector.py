# app/memory/injector.py
"""MemoryInjector - Composes memory content into system prompt at session start.

Reference: OpenClaw session start memory loading:
- memory/YYYY-MM-DD.md (today + yesterday) always loaded
- MEMORY.md loaded only in main (private) session mode
"""
from typing import Literal, Optional

from app.memory.markdown_memory import MarkdownMemoryManager
from app.memory.daily_log import DailyLogManager


class MemoryInjector:
    """Composes memory content for injection into system prompt at session start.

    Memory loaded per session mode:
    - "main":   MEMORY.md + today + yesterday daily logs
    - "shared": today + yesterday daily logs only
    """

    def __init__(
        self,
        memory_manager: Optional[MarkdownMemoryManager] = None,
        daily_log_manager: Optional[DailyLogManager] = None,
    ):
        if memory_manager is None:
            memory_manager = MarkdownMemoryManager()
        if daily_log_manager is None:
            daily_log_manager = DailyLogManager()
        self.memory_manager = memory_manager
        self.daily_log_manager = daily_log_manager

    async def load_session_memory(
        self,
        user_id: str,
        session_id: str,
        mode: Literal["main", "shared"] = "main",
        query: Optional[str] = None,
    ) -> str:
        """Load all relevant memory for a session and compose as markdown string.

        Args:
            user_id: user identifier
            session_id: current session identifier
            mode: "main" (includes MEMORY.md) or "shared" (daily logs only)
            query: optional search query for RAG retrieval (Phase 4)

        Returns:
            Markdown string to inject into system prompt under '## Memory' section.
        """
        parts = []

        # Daily logs (today + yesterday) — always loaded
        daily_content = self.daily_log_manager.read_today_and_yesterday()
        if daily_content:
            parts.append(f"## 今日与昨日会话日志\n\n{daily_content}")

        # Long-term memory — only in main private session
        if mode == "main":
            memory_content = self.memory_manager.get_memory()
            if memory_content:
                parts.append(f"## 长期记忆 (MEMORY.md)\n\n{memory_content}")

        return "\n\n".join(parts) if parts else ""


# Singleton
_injector: Optional["MemoryInjector"] = None


def get_memory_injector() -> "MemoryInjector":
    """Get the singleton MemoryInjector instance."""
    global _injector
    if _injector is None:
        _injector = MemoryInjector()
    return _injector
