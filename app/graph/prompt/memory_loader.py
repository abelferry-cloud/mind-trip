"""app/graph/prompt/memory_loader.py — Layer 3: Session Memory 加载器。

加载 Layer 3: 今日+昨日日志 + (仅 main) MEMORY.md。
组合为 "## Memory" 区段字符串。

Token 预算控制由本类负责：分阶段截断直到在预算内。
"""
from typing import Literal, Optional

from app.services.memory import DailyLogManager
from app.services.memory import MarkdownMemoryManager


class MemoryLoader:
    """加载 Layer 3: 今日+昨日日志 + (仅 main) MEMORY.md。

    组合为 "## Memory" 区段字符串。

    Token 预算控制由本类负责：分阶段截断直到在预算内
    （先截断 MEMORY.md，再截断较旧的日志条目）。
    使用字符数近似控制（1 token ≈ 4 字符），不调用外部 token 计数库。
    """

    def __init__(
        self,
        daily_log_manager: Optional[DailyLogManager] = None,
        memory_manager: Optional[MarkdownMemoryManager] = None,
        max_chars: int = 8000,  # ~2,000 tokens
    ):
        self._daily_log_manager = daily_log_manager or DailyLogManager()
        self._memory_manager = memory_manager or MarkdownMemoryManager()
        self._max_chars = max_chars

    def load(
        self,
        user_id: str,
        session_id: str,
        mode: Literal["main", "shared"] = "main",
    ) -> str:
        """加载会话记忆并组合为 markdown 字符串。

        - 日志（今日 + 昨日）始终加载
        - MEMORY.md 仅在 main 模式下加载
        """
        parts = []

        # 今日 + 昨日日志
        daily_content = self._daily_log_manager.read_today_and_yesterday()
        if daily_content:
            parts.append(f"## 今日与昨日会话日志\n\n{daily_content}")

        # 长期记忆 — 仅 main
        if mode == "main":
            memory_content = self._memory_manager.get_memory()
            if memory_content:
                parts.append(f"## 长期记忆 (MEMORY.md)\n\n{memory_content}")

        # Token 预算控制：分阶段截断
        combined = self._enforce_budget(parts, self._max_chars)
        return combined

    def _enforce_budget(self, parts: list[str], max_chars: int) -> str:
        """分阶段截断直到符合字符预算。"""
        if not parts:
            return ""

        # 先尝试直接组合
        combined = "\n\n".join(parts)
        if len(combined) <= max_chars:
            return combined

        # 阶段 1: MEMORY.md 截断（假设它在 parts[-1]）
        if len(parts) > 1 and len(parts[-1]) > max_chars // 2:
            memory_part = parts[-1]
            header_end = memory_part.index("\n\n") + 2 if "\n\n" in memory_part else 0
            memory_body = memory_part[header_end:]
            sentinel = "\n\n[... MEMORY.md 内容已截断]"
            truncated_body = memory_body[: max_chars // 2 - len(sentinel)] + sentinel
            parts[-1] = memory_part[:header_end] + truncated_body
            combined = "\n\n".join(parts)
            if len(combined) <= max_chars:
                return combined

        # 阶段 2: 较旧日志截断（从头开始，逐条移除直到符合预算）
        # assumption: parts[0] is the oldest daily log entry (today+yesterday ordering from load())
        result_parts = list(parts)
        while len(result_parts) > 1 and len("\n\n".join(result_parts)) > max_chars:
            result_parts.pop(0)  # 移除最旧的日志
        combined = "\n\n".join(result_parts)

        # 阶段 3: 硬截断
        if len(combined) > max_chars:
            combined = combined[:max_chars] + "\n\n[... 内容已截断以符合 token 预算]"

        return combined
