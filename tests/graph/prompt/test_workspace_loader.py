"""tests/graph/prompt/test_workspace_loader.py"""
import pytest
from pathlib import Path
from app.graph.prompt.workspace_loader import WorkspaceLoader
from app.graph.prompt.config import WORKSPACE_DIR

@pytest.fixture
def temp_workspace(tmp_path, monkeypatch):
    wp = tmp_path / "workspace"
    wp.mkdir()
    monkeypatch.setattr("app.graph.prompt.workspace_loader.WORKSPACE_DIR", wp)
    return wp

def test_loads_core_files_in_order(temp_workspace, monkeypatch):
    monkeypatch.setattr("app.graph.prompt.workspace_loader.WORKSPACE_DIR", temp_workspace)
    # 创建部分 workspace 文件
    (temp_workspace / "SOUL.md").write_text("Soul content", encoding="utf-8")
    (temp_workspace / "AGENTS.md").write_text("Agents content", encoding="utf-8")
    (temp_workspace / "USER.md").write_text("User content", encoding="utf-8")
    # BOOTSTRAP.md 不存在

    loader = WorkspaceLoader(mode="shared")
    result = loader.invoke({})

    assert "## SOUL" in result["workspace_prompt"]
    assert "## AGENTS" in result["workspace_prompt"]
    assert "## USER" in result["workspace_prompt"]
    assert "## BOOTSTRAP" not in result["workspace_prompt"]  # 不存在则跳过
    assert "MEMORY.md" not in result["workspace_prompt"]  # shared 模式不加载

def test_main_mode_includes_memory_md(temp_workspace, monkeypatch):
    monkeypatch.setattr("app.graph.prompt.workspace_loader.WORKSPACE_DIR", temp_workspace)
    (temp_workspace / "SOUL.md").write_text("Soul", encoding="utf-8")
    (temp_workspace / "MEMORY.md").write_text("Memory content", encoding="utf-8")

    loader = WorkspaceLoader(mode="main")
    result = loader.invoke({})

    assert "## MEMORY" in result["workspace_prompt"]

def test_session_mode_override_in_invoke(temp_workspace, monkeypatch):
    monkeypatch.setattr("app.graph.prompt.workspace_loader.WORKSPACE_DIR", temp_workspace)
    (temp_workspace / "SOUL.md").write_text("Soul", encoding="utf-8")
    (temp_workspace / "MEMORY.md").write_text("Memory content", encoding="utf-8")

    loader = WorkspaceLoader(mode="shared")  # 初始化为 shared
    result = loader.invoke({"session_mode": "main"})  # 但调用时覆盖为 main

    assert "## MEMORY" in result["workspace_prompt"]  # main 模式应加载 MEMORY

def test_returns_workspace_loaded_at_timestamp(temp_workspace, monkeypatch):
    monkeypatch.setattr("app.graph.prompt.workspace_loader.WORKSPACE_DIR", temp_workspace)
    (temp_workspace / "SOUL.md").write_text("Soul", encoding="utf-8")

    loader = WorkspaceLoader()
    result = loader.invoke({})
    assert "workspace_loaded_at" in result
    assert "T" in result["workspace_loaded_at"]  # ISO format
