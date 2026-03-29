# app/memory/injector.py
"""MemoryInjector - 在会话开始时将记忆内容组合到 system prompt 中。

参考：OpenClaw 会话开始时的记忆加载：
- memory/YYYY-MM-DD.md（今日 + 昨日）始终加载
- MEMORY.md 仅在 main（私有）会话模式下加载
"""
from typing import Literal, Optional

from app.memory.markdown_memory import MarkdownMemoryManager
from app.memory.daily_log import DailyLogManager


class MemoryInjector:
    """在会话开始时组合记忆内容以注入到 system prompt。

    按会话模式加载记忆：
    - "main":   MEMORY.md + 今日 + 昨日日志
    - "shared": 仅今日 + 昨日日志
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
        """为会话加载所有相关记忆并组合为 markdown 字符串。

        Args:
            user_id: 用户标识符
            session_id: 当前会话标识符
            mode: "main"（包含 MEMORY.md）或 "shared"（仅日志）
            query: 可选的搜索查询用于 RAG 检索（第 4 阶段）

        Returns:
            要注入到 system prompt 的 Markdown 字符串（'## Memory' 部分）。
        """
        parts = []

        # 日志（今日 + 昨日）— 始终加载
        daily_content = self.daily_log_manager.read_today_and_yesterday()
        if daily_content:
            parts.append(f"## 今日与昨日会话日志\n\n{daily_content}")

        # 长期记忆 — 仅在 main 私有会话中
        if mode == "main":
            memory_content = self.memory_manager.get_memory()
            if memory_content:
                parts.append(f"## 长期记忆 (MEMORY.md)\n\n{memory_content}")

        return "\n\n".join(parts) if parts else ""


# Singleton
_injector: Optional["MemoryInjector"] = None


def get_memory_injector() -> "MemoryInjector":
    """获取单例 MemoryInjector 实例。"""
    global _injector
    if _injector is None:
        _injector = MemoryInjector()
    return _injector
