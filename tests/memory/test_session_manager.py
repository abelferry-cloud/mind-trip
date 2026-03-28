# tests/memory/test_session_manager.py
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.memory.session_manager import SessionMemoryManager


def test_session_isolation():
    """测试不同 session_id 有独立的 memory 实例"""
    manager = SessionMemoryManager()

    mem1 = manager.get_memory("session_001")
    mem2 = manager.get_memory("session_002")

    # 同一 session_id 返回同一实例
    assert manager.get_memory("session_001") is mem1
    # 不同 session_id 返回不同实例
    assert mem1 is not mem2


def test_save_and_get_context():
    """测试保存和获取对话上下文"""
    manager = SessionMemoryManager()
    mem = manager.get_memory("session_test")

    mem.save_context({"input": "你好"}, {"output": "你好！有什么可以帮您？"})
    mem.save_context({"input": "我想去成都"}, {"output": "成都是很棒的选择！"})

    messages = mem.get_history()
    assert len(messages) == 4  # 2 pairs = 4 messages


def test_clear_session():
    """测试清除某个 session 的记忆"""
    manager = SessionMemoryManager()
    mem = manager.get_memory("session_clear")

    mem.save_context({"input": "test"}, {"output": "test response"})
    assert len(mem.get_history()) == 2

    manager.clear_session("session_clear")
    assert len(mem.get_history()) == 0