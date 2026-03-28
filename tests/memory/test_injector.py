import pytest
import tempfile
from pathlib import Path
from app.memory.injector import MemoryInjector
from app.memory.markdown_memory import MarkdownMemoryManager
from app.memory.daily_log import DailyLogManager

@pytest.fixture
def temp_workspace(tmp_path):
    mem_dir = tmp_path / "memory"
    mem_dir.mkdir()
    mem_file = tmp_path / "MEMORY.md"
    return {"mem_dir": mem_dir, "mem_file": mem_file}

def test_load_session_memory_main_mode_includes_memory_and_daily(temp_workspace):
    """mode=main loads MEMORY.md + today + yesterday."""
    mem_mgr = MarkdownMemoryManager(memory_path=temp_workspace["mem_file"])
    dl_mgr = DailyLogManager(memory_dir=temp_workspace["mem_dir"])
    inj = MemoryInjector(mem_mgr, dl_mgr)

    # Write something to MEMORY.md
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        mem_mgr.update_preference("user_001", "spending_style", "节省")
    )

    # Write something to daily log
    dl_mgr.append("sess_001", "user_001", "hello", "hi")

    result = asyncio.get_event_loop().run_until_complete(
        inj.load_session_memory("user_001", "sess_001", mode="main")
    )
    assert "节省" in result
    assert "hello" in result

def test_load_session_memory_shared_mode_skips_memory(temp_workspace):
    """mode=shared skips MEMORY.md, only loads daily logs."""
    mem_mgr = MarkdownMemoryManager(memory_path=temp_workspace["mem_file"])
    dl_mgr = DailyLogManager(memory_dir=temp_workspace["mem_dir"])
    inj = MemoryInjector(mem_mgr, dl_mgr)

    import asyncio
    asyncio.get_event_loop().run_until_complete(
        mem_mgr.update_preference("user_001", "spending_style", "节省")
    )
    dl_mgr.append("sess_001", "user_001", "hello", "hi")

    result = asyncio.get_event_loop().run_until_complete(
        inj.load_session_memory("user_001", "sess_001", mode="shared")
    )
    assert "节省" not in result  # MEMORY.md skipped
    assert "hello" in result     # daily log included