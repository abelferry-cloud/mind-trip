"""DailyLogManager - 每日日志管理器，在 memory/YYYY-MM-DD.md 追加会话日志。

参考：OpenClaw memory/YYYY-MM-DD.md 每日会话日志格式。
"""
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from filelock import FileLock

_daily_log_manager: Optional["DailyLogManager"] = None


def get_daily_log_manager() -> "DailyLogManager":
    """获取单例 DailyLogManager 实例。"""
    global _daily_log_manager
    if _daily_log_manager is None:
        _daily_log_manager = DailyLogManager()
    return _daily_log_manager


class DailyLogManager:
    """追加式每日会话日志。

    文件格式（每个 logs/YYYY-MM-DD.md）:
        # 2026-03-28

        ## Session: abc123

        [20:45:33]
        Human: message
        AI: response

        ## Session: def456
        ...
    """

    def __init__(self, memory_dir: Optional[str] = None):
        if memory_dir is None:
            memory_dir = Path(__file__).parent / "logs"
        else:
            memory_dir = Path(memory_dir) / "logs"
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def _get_date_file(self, date: datetime) -> Path:
        return self.memory_dir / f"{date.strftime('%Y-%m-%d')}.md"

    def _session_block_exists(self, session_id: str, content: str) -> bool:
        return f"## Session: {session_id}" in content

    def append(
        self,
        session_id: str,
        user_id: str,
        human_message: str,
        ai_message: str,
    ) -> None:
        """将人类/AI 消息对追加到今日日志。

        使用文件锁保证并发安全。
        如果是该会话今日第一条消息则创建会话块。
        """
        now = datetime.now()
        date_file = self._get_date_file(now)
        lock_file = date_file.with_suffix(".lock")

        lock = FileLock(str(lock_file), timeout=10)
        with lock:
            existing = date_file.read_text(encoding="utf-8") if date_file.exists() else ""

            # Determine mode
            mode = "a" if date_file.exists() else "w"

            with open(date_file, mode, encoding="utf-8") as f:
                if mode == "w":
                    f.write(f"# {now.strftime('%Y-%m-%d')}\n\n")
                if not self._session_block_exists(session_id, existing):
                    f.write(f"## Session: {session_id}\n\n")
                timestamp = now.strftime("%H:%M:%S")
                f.write(f"[{timestamp}]\n")
                f.write(f"Human: {human_message}\n")
                f.write(f"AI: {ai_message}\n\n")

    def read_today_and_yesterday(self) -> str:
        """读取今日和昨日的日志（拼接）。"""
        now = datetime.now()
        yesterday = now - timedelta(days=1)

        result = ""
        for d in [yesterday, now]:
            f = self._get_date_file(d)
            if f.exists():
                result += f.read_text(encoding="utf-8") + "\n"
            else:
                result += f"# {d.strftime('%Y-%m-%d')}\n\n"
        return result

    def read_session(self, session_id: str) -> str:
        """读取特定会话的所有条目（跨日志文件）。

        按日期顺序扫描所有 logs/*.md 文件（从旧到新）。
        如果未找到会话则返回空字符串。
        """
        if not self.memory_dir.exists():
            return ""

        session_blocks = []
        for f in sorted(self.memory_dir.glob("*.md")):
            content = f.read_text(encoding="utf-8")
            # Find all session blocks
            pattern = rf"(## Session: {re.escape(session_id)}.*?)(?=\n## Session: |\n---|\Z)"
            for match in re.finditer(pattern, content, re.DOTALL):
                block = match.group(1).strip()
                if block:
                    session_blocks.append(block)

        return "\n\n".join(session_blocks)