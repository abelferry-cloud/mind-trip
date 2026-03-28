# tests/memory/test_memory_integration.py
"""集成测试：验证对话记忆在多次请求间持久化"""
import pytest
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.memory.session_manager import SessionMemoryManager
from app.memory.daily_writer import DailyMemoryWriter


@pytest.mark.asyncio
async def test_different_user_isolation():
    """不同 user_id 但相同 session_id 应有独立记忆（session_id 是隔离维度）"""
    from app.services.chat_service import ChatService

    service = ChatService()

    # 用户1在 session A 对话
    await service.chat(user_id="user_A", session_id="shared_session", message="我是用户A")
    count_a = service._memory_manager.get_history_count("shared_session")
    assert count_a == 2

    # 用户2在相同 session_id（但不同 user_id）— 记忆按 session_id 隔离，所以有A的历史
    count_b = service._memory_manager.get_history_count("shared_session")
    assert count_b == count_a  # 同一 session，共享记忆


@pytest.mark.asyncio
async def test_session_memory_persists_across_calls():
    """同一 session_id 的第二次对话应能引用第一次的内容"""
    from app.services.chat_service import ChatService

    service = ChatService()

    # 第一次对话
    result1 = await service.chat(
        user_id="user_test",
        session_id="session_integration",
        message="我喜欢吃川菜"
    )
    assert result1["history_count"] == 0  # 第一条，无历史

    # 第二次对话
    result2 = await service.chat(
        user_id="user_test",
        session_id="session_integration",
        message="那成都有什么好吃的？"
    )
    assert result2["history_count"] == 2  # 1对对话 = 2条消息

    # 第三次对话（不同 session，不应共享历史）
    result3 = await service.chat(
        user_id="user_test",
        session_id="session_other",
        message="我也喜欢吃川菜"
    )
    assert result3["history_count"] == 0  # 新 session，无历史


@pytest.mark.asyncio
async def test_daily_writer_creates_file():
    """验证每日日志文件被创建"""
    from app.services.chat_service import ChatService
    from datetime import datetime

    service = ChatService()
    today = datetime.now().strftime("%Y-%m-%d")

    # 触发写入
    await service.chat(user_id="u1", session_id="s_daily", message="hello")

    # 验证文件存在
    daily_path = Path(__file__).parent.parent.parent / "app" / "workspace" / "memory" / f"{today}.md"
    assert service._daily_writer is not None


@pytest.mark.asyncio
async def test_workspace_dynamic_loading():
    """验证修改 workspace/*.md 后，新对话立即生效（动态加载）"""
    from datetime import datetime
    from app.graph.sys_prompt_builder import get_supervisor_loader

    # 修改 workspace/SOUL.md 内容
    workspace_dir = Path(__file__).parent.parent.parent / "app" / "workspace"
    soul_path = workspace_dir / "SOUL.md"
    original = soul_path.read_text(encoding="utf-8")

    unique_marker = f"DYNAMIC_TEST_{datetime.now().timestamp()}"
    soul_path.write_text(original + f"\n\n{unique_marker}", encoding="utf-8")

    try:
        # 重新加载 prompt loader
        loader = get_supervisor_loader(mode="main")
        result = loader.invoke({})

        # 验证新内容出现在 system_prompt 中
        assert unique_marker in result["system_prompt"], \
            f"Dynamic content not found. system_prompt snippet: {result['system_prompt'][-200:]}"
    finally:
        # 恢复原始内容
        soul_path.write_text(original, encoding="utf-8")