"""每日日志写入器 - 追加写入 workspace/memory/YYYY-MM-DD.md"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class DailyMemoryWriter:
    """将对话追加写入每日日志文件。

    文件路径: {base_dir}/YYYY-MM-DD.md
    格式:
        # 2026-03-28

        ## Session: abc123

        [20:45:33]
        Human: 消息内容
        AI: 回复内容

        ## Session: def456
        ...
    """

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = Path(__file__).parent.parent / "workspace" / "memory"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self) -> Path:
        """获取今日日志文件路径。"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.base_dir / f"{today}.md"

    def _session_block_exists(self, session_id: str, content: str) -> bool:
        """检查 session 是否已存在（是否需要新建 block）。"""
        return f"## Session: {session_id}" in content

    def append(
        self,
        session_id: str,
        user_id: str,
        human_message: str,
        ai_message: str,
    ) -> None:
        """追加一条对话到每日日志。

        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            human_message: 用户消息
            ai_message: AI 回复
        """
        file_path = self._get_file_path()
        now = datetime.now()
        timestamp = now.strftime("%H:%M:%S")
        date_str = now.strftime("%Y-%m-%d")

        # 读取现有内容
        existing_content = ""
        if file_path.exists():
            existing_content = file_path.read_text(encoding="utf-8")

        # 构建新记录
        new_records = []

        # 如果文件不存在或没有日期标题，先加标题
        if not existing_content.strip():
            new_records.append(f"# {date_str}\n")
        elif f"# {date_str}" not in existing_content:
            new_records.append(f"\n# {date_str}\n")

        # 如果 session block 不存在，先加 session 标题
        if not self._session_block_exists(session_id, existing_content):
            new_records.append(f"\n## Session: {session_id}\n")

        # 添加消息记录
        new_records.append(f"[{timestamp}]\n")
        new_records.append(f"Human: {human_message}\n")
        new_records.append(f"AI: {ai_message}\n")

        # 写入文件
        new_content = "".join(new_records)
        if file_path.exists():
            file_path.write_text(existing_content + new_content, encoding="utf-8")
        else:
            file_path.write_text(new_content, encoding="utf-8")

    def read_today(self) -> str:
        """读取今日日志内容。"""
        file_path = self._get_file_path()
        if not file_path.exists():
            return ""
        return file_path.read_text(encoding="utf-8")