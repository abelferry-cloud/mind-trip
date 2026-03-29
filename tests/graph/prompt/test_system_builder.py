"""tests/graph/prompt/test_system_builder.py"""
import pytest
import tempfile
from pathlib import Path
from app.graph.prompt.system_builder import SystemPromptBuilder

@pytest.fixture
def temp_workspace(tmp_path):
    wp = tmp_path / "workspace"
    wp.mkdir()
    return wp

def test_load_existing_file(temp_workspace, monkeypatch):
    monkeypatch.setattr("app.graph.prompt.system_builder.WORKSPACE_DIR", temp_workspace)
    (temp_workspace / "SYSTEM_PROMPT_supervisor.md").write_text("---\ndate: 2026\n---\n你是一个主管 Agent", encoding="utf-8")
    sb = SystemPromptBuilder()
    result = sb.load("supervisor")
    assert "你是一个主管 Agent" in result
    assert "date: 2026" not in result  # frontmatter stripped

def test_load_nonexistent_file(temp_workspace, monkeypatch):
    monkeypatch.setattr("app.graph.prompt.system_builder.WORKSPACE_DIR", temp_workspace)
    sb = SystemPromptBuilder()
    result = sb.load("nonexistent_agent")
    assert result == ""

def test_load_file_without_frontmatter(temp_workspace, monkeypatch):
    monkeypatch.setattr("app.graph.prompt.system_builder.WORKSPACE_DIR", temp_workspace)
    (temp_workspace / "SYSTEM_PROMPT_attractions.md").write_text("你是一个景点 Agent", encoding="utf-8")
    sb = SystemPromptBuilder()
    result = sb.load("attractions")
    assert result == "你是一个景点 Agent"