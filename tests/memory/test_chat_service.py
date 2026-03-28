# tests/memory/test_chat_service.py
import pytest
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.memory.session_manager import SessionMemoryManager
from app.memory.daily_writer import DailyMemoryWriter


def test_memory_integration_structure():
    """测试 ChatService 是否正确集成了记忆组件"""
    from app.services.chat_service import ChatService

    service = ChatService()

    # 验证有 _memory_manager
    assert hasattr(service, "_memory_manager")
    assert isinstance(service._memory_manager, SessionMemoryManager)

    # 验证有 _daily_writer
    assert hasattr(service, "_daily_writer")
    assert isinstance(service._daily_writer, DailyMemoryWriter)


def test_history_format():
    """测试对话历史格式化"""
    from app.services.chat_service import ChatService

    service = ChatService()
    mem = service._memory_manager.get_memory("test_session")

    # 添加一些对话
    mem.save_context({"input": "你好"}, {"output": "你好！"})
    mem.save_context({"input": "我想旅游"}, {"output": "去哪？"})

    # 获取格式化后的历史
    history = service._format_history(mem.get_history())

    assert "Human: 你好" in history
    assert "AI: 你好！" in history
    assert "Human: 我想旅游" in history
    assert "AI: 去哪？" in history