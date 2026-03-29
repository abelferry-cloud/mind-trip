"""tests/graph/prompt/test_composer.py"""
import pytest
from pathlib import Path
from unittest.mock import Mock

from app.graph.prompt.composer import PromptComposer


@pytest.fixture
def temp_workspace(tmp_path, monkeypatch):
    wp = tmp_path / "workspace"
    wp.mkdir()
    mem_dir = wp / "memory"
    mem_dir.mkdir()
    mem_file = wp / "MEMORY.md"
    monkeypatch.setattr("app.graph.prompt.config.WORKSPACE_DIR", wp)
    monkeypatch.setattr("app.graph.prompt.config.MEMORY_DIR", mem_dir)
    return {"workspace": wp, "mem_dir": mem_dir, "mem_file": mem_file}


def test_compose_combines_three_layers(temp_workspace):
    from app.memory.daily_log import DailyLogManager
    from app.memory.markdown_memory import MarkdownMemoryManager
    from app.graph.prompt.memory_loader import MemoryLoader

    # 创建 workspace 文件
    (temp_workspace["workspace"] / "SYSTEM_PROMPT_supervisor.md").write_text("Supervisor system prompt", encoding="utf-8")
    (temp_workspace["workspace"] / "SOUL.md").write_text("Soul content", encoding="utf-8")
    (temp_workspace["workspace"] / "AGENTS.md").write_text("Agents content", encoding="utf-8")
    (temp_workspace["mem_file"]).write_text("Memory content", encoding="utf-8")

    # 创建 daily log
    dl_mgr = DailyLogManager(memory_dir=temp_workspace["mem_dir"])
    mem_mgr = MarkdownMemoryManager(memory_path=temp_workspace["mem_file"])
    dl_mgr.append("sess_001", "user_001", "hello", "hi")

    # Mock SystemPromptBuilder to return specific content
    mock_system_builder = Mock()
    mock_system_builder.load.return_value = "Supervisor system prompt"

    # Mock WorkspaceLoader to return temp workspace content
    mock_workspace_loader = Mock()
    mock_workspace_loader.invoke.return_value = {
        "workspace_prompt": "## SOUL\n\nSoul content\n## AGENTS\n\nAgents content\n"
    }

    # Mock MemoryLoader to use the real managers but return predictable content
    real_memory_loader = MemoryLoader(dl_mgr, mem_mgr)

    composer = PromptComposer(agent_name="supervisor", agent_type="Planning", mode="main")
    composer._system_builder = mock_system_builder
    composer._workspace_loader = mock_workspace_loader
    composer._memory_loader = real_memory_loader

    result = composer.invoke({"user_id": "user_001", "session_id": "sess_001"})

    assert "Supervisor system prompt" in result["system_prompt"]
    assert "Soul content" in result["system_prompt"]
    assert "hello" in result["system_prompt"]
    assert "Memory content" in result["system_prompt"]
    assert result["agent_name"] == "supervisor"
    assert result["mode"] == "main"


def test_shared_mode_skips_memory(temp_workspace):
    from app.memory.daily_log import DailyLogManager
    from app.memory.markdown_memory import MarkdownMemoryManager
    from app.graph.prompt.memory_loader import MemoryLoader
    from app.graph.prompt.system_builder import SystemPromptBuilder

    (temp_workspace["workspace"] / "SYSTEM_PROMPT_supervisor.md").write_text("Supervisor system prompt", encoding="utf-8")
    (temp_workspace["workspace"] / "SOUL.md").write_text("Soul content", encoding="utf-8")
    (temp_workspace["mem_file"]).write_text("Memory content", encoding="utf-8")

    dl_mgr = DailyLogManager(memory_dir=temp_workspace["mem_dir"])
    mem_mgr = MarkdownMemoryManager(memory_path=temp_workspace["mem_file"])
    dl_mgr.append("sess_001", "user_001", "hello", "hi")

    # Mock WorkspaceLoader
    mock_workspace_loader = Mock()
    mock_workspace_loader.invoke.return_value = {
        "workspace_prompt": "## SOUL\n\nSoul content\n"
    }

    composer = PromptComposer(agent_name="supervisor", agent_type="Planning", mode="shared")
    composer._system_builder = SystemPromptBuilder()
    composer._workspace_loader = mock_workspace_loader
    composer._memory_loader = MemoryLoader(dl_mgr, mem_mgr)

    result = composer.invoke({"user_id": "user_001", "session_id": "sess_001"})

    assert "Memory content" not in result["system_prompt"]  # shared 跳过 MEMORY
    assert "hello" in result["system_prompt"]  # 日志仍加载


def test_invoker_session_mode_override(temp_workspace):
    from app.memory.daily_log import DailyLogManager
    from app.memory.markdown_memory import MarkdownMemoryManager
    from app.graph.prompt.memory_loader import MemoryLoader
    from app.graph.prompt.system_builder import SystemPromptBuilder

    (temp_workspace["workspace"] / "SYSTEM_PROMPT_supervisor.md").write_text("Supervisor", encoding="utf-8")
    (temp_workspace["workspace"] / "SOUL.md").write_text("Soul", encoding="utf-8")
    (temp_workspace["mem_file"]).write_text("Memory content", encoding="utf-8")

    dl_mgr = DailyLogManager(memory_dir=temp_workspace["mem_dir"])
    mem_mgr = MarkdownMemoryManager(memory_path=temp_workspace["mem_file"])

    # Mock WorkspaceLoader
    mock_workspace_loader = Mock()
    mock_workspace_loader.invoke.return_value = {
        "workspace_prompt": "## SOUL\n\nSoul\n"
    }

    composer = PromptComposer(agent_name="supervisor", mode="shared")  # 初始化为 shared
    composer._system_builder = SystemPromptBuilder()
    composer._workspace_loader = mock_workspace_loader
    composer._memory_loader = MemoryLoader(dl_mgr, mem_mgr)

    # 但调用时覆盖为 main
    result = composer.invoke({"user_id": "user_001", "session_id": "sess_001", "session_mode": "main"})
    assert "Memory content" in result["system_prompt"]  # main 模式覆盖