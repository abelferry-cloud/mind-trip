import pytest
import tempfile
import asyncio
from pathlib import Path
from app.memory.markdown_memory import MarkdownMemoryManager, MEMORY_TEMPLATE

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)

def test_get_memory_returns_empty_when_file_missing(temp_dir):
    """Missing MEMORY.md returns empty string."""
    mgr = MarkdownMemoryManager(memory_path=temp_dir / "MEMORY.md")
    result = mgr.get_memory()
    assert result == ""

def test_get_memory_returns_content_when_file_exists(temp_dir):
    """Existing MEMORY.md returns its content."""
    mem_file = temp_dir / "MEMORY.md"
    mem_file.write_text("# MEMORY.md\n\n## User Profile\n\n- **Name**: 张三", encoding="utf-8")
    mgr = MarkdownMemoryManager(memory_path=mem_file)
    result = mgr.get_memory()
    assert "张三" in result

@pytest.mark.asyncio
async def test_update_preference_creates_file_if_missing(temp_dir):
    """update_preference creates MEMORY.md from template if missing."""
    mgr = MarkdownMemoryManager(memory_path=temp_dir / "MEMORY.md")
    await mgr.update_preference("user_001", "spending_style", "节省")
    mem_file = temp_dir / "MEMORY.md"
    assert mem_file.exists()
    content = mem_file.read_text(encoding="utf-8")
    assert "节省" in content

@pytest.mark.asyncio
async def test_update_preference_appends_to_existing_file(temp_dir):
    """update_preference appends new preference to existing MEMORY.md."""
    mem_file = temp_dir / "MEMORY.md"
    mem_file.write_text("# MEMORY.md\n\n## Travel Preferences\n\n- **Hardships to avoid**: 硬座\n", encoding="utf-8")
    mgr = MarkdownMemoryManager(memory_path=mem_file)
    await mgr.update_preference("user_001", "health", "心脏病")
    content = mem_file.read_text(encoding="utf-8")
    assert "硬座" in content
    assert "心脏病" in content

@pytest.mark.asyncio
async def test_update_user_profile_replaces_profile_section(temp_dir):
    """update_user_profile replaces existing User Profile section."""
    mem_file = temp_dir / "MEMORY.md"
    mem_file.write_text("# MEMORY.md\n\n## User Profile\n\n- **Name**: 李四\n", encoding="utf-8")
    mgr = MarkdownMemoryManager(memory_path=mem_file)
    await mgr.update_user_profile("user_001", {
        "name": "王五",
        "preferred_name": "小王",
        "timezone": "Asia/Shanghai",
    })
    content = mem_file.read_text(encoding="utf-8")
    assert "王五" in content
    assert "小王" in content
    assert "李四" not in content  # old name replaced
