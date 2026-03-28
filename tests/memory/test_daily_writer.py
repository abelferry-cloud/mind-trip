# tests/memory/test_daily_writer.py
import pytest
import tempfile
import os
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.memory.daily_writer import DailyMemoryWriter


def test_append_to_daily_log():
    """测试追加写入每日日志文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        writer = DailyMemoryWriter(base_dir=tmpdir)

        # 写入第一条记录
        writer.append(
            session_id="session_001",
            user_id="user_001",
            human_message="我想去成都",
            ai_message="成都是很棒的选择！您计划几天？"
        )

        # 验证文件存在
        today = datetime.now().strftime("%Y-%m-%d")
        expected_path = Path(tmpdir) / f"{today}.md"
        assert expected_path.exists()

        content = expected_path.read_text(encoding="utf-8")
        assert "session_001" in content
        assert "我想去成都" in content
        assert "成都是很棒的选择" in content

        # 写入第二条记录（同一 session）
        writer.append(
            session_id="session_001",
            user_id="user_001",
            human_message="3天",
            ai_message="3天的话可以逛主要景点。"
        )

        content = expected_path.read_text(encoding="utf-8")
        # 验证第二条记录也存在于同一 session 中
        assert "Human: 3天" in content
        assert "AI: 3天的话可以逛主要景点。" in content

        # 写入新 session
        writer.append(
            session_id="session_002",
            user_id="user_001",
            human_message="另外，我想去重庆",
            ai_message="重庆和成都很近，可以一起玩。"
        )

        content = expected_path.read_text(encoding="utf-8")
        assert "session_002" in content


def test_creates_directory_if_not_exists():
    """测试目录不存在时自动创建"""
    with tempfile.TemporaryDirectory() as tmpdir:
        writer = DailyMemoryWriter(base_dir=tmpdir + "/new_dir/memory")
        writer.append("s1", "u1", "hi", "hello")
        assert (Path(tmpdir) / "new_dir/memory").exists()