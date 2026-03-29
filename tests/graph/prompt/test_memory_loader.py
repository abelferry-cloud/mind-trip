"""tests/graph/prompt/test_memory_loader.py"""
import pytest
from pathlib import Path
from app.graph.prompt.memory_loader import MemoryLoader


@pytest.fixture
def temp_workspace(tmp_path):
    mem_dir = tmp_path / "memory"
    mem_dir.mkdir()
    mem_file = tmp_path / "MEMORY.md"
    return {"mem_dir": mem_dir, "mem_file": mem_file}


def test_load_combines_daily_and_memory(temp_workspace):
    from app.memory.daily_log import DailyLogManager
    from app.memory.markdown_memory import MarkdownMemoryManager
    dl_mgr = DailyLogManager(memory_dir=temp_workspace["mem_dir"])
    mem_mgr = MarkdownMemoryManager(memory_path=temp_workspace["mem_file"])
    loader = MemoryLoader(dl_mgr, mem_mgr)

    dl_mgr.append("sess_001", "user_001", "hello", "hi")
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        mem_mgr.update_preference("user_001", "spending_style", "节省")
    )

    result = loader.load("user_001", "sess_001", mode="main")
    assert "hello" in result
    assert "节省" in result


def test_shared_mode_skips_memory(temp_workspace):
    from app.memory.daily_log import DailyLogManager
    from app.memory.markdown_memory import MarkdownMemoryManager
    dl_mgr = DailyLogManager(memory_dir=temp_workspace["mem_dir"])
    mem_mgr = MarkdownMemoryManager(memory_path=temp_workspace["mem_file"])
    loader = MemoryLoader(dl_mgr, mem_mgr)

    dl_mgr.append("sess_001", "user_001", "hello", "hi")
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        mem_mgr.update_preference("user_001", "spending_style", "节省")
    )

    result = loader.load("user_001", "sess_001", mode="shared")
    assert "hello" in result
    assert "节省" not in result  # MEMORY.md skipped in shared mode


def test_enforce_budget_truncates_long_memory(temp_workspace):
    from app.memory.daily_log import DailyLogManager
    from app.memory.markdown_memory import MarkdownMemoryManager
    dl_mgr = DailyLogManager(memory_dir=temp_workspace["mem_dir"])
    mem_mgr = MarkdownMemoryManager(memory_path=temp_workspace["mem_file"])
    # max_chars=200 足够小，强制触发截断
    loader = MemoryLoader(dl_mgr, mem_mgr, max_chars=200)

    # 写入大量 MEMORY 内容
    long_content = "x" * 500
    mem_mgr.memory_path.write_text(f"# MEMORY\n\n{long_content}", encoding="utf-8")
    dl_mgr.append("sess_001", "user_001", "hello", "hi")

    result = loader.load("user_001", "sess_001", mode="main")
    assert len(result) <= 200 + 50  # 允许一些 sentinel 开销
    assert "..." in result or "截断" in result  # 截断标记存在


def test_enforce_budget_preserves_short_content(temp_workspace):
    from app.memory.daily_log import DailyLogManager
    from app.memory.markdown_memory import MarkdownMemoryManager
    dl_mgr = DailyLogManager(memory_dir=temp_workspace["mem_dir"])
    mem_mgr = MarkdownMemoryManager(memory_path=temp_workspace["mem_file"])
    loader = MemoryLoader(dl_mgr, mem_mgr, max_chars=8000)

    dl_mgr.append("sess_001", "user_001", "hi", "hello")

    result = loader.load("user_001", "sess_001", mode="main")
    assert "hi" in result
    assert "hello" in result