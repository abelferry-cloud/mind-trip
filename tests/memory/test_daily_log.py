import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from app.memory.daily_log import DailyLogManager

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)

@pytest.fixture
def manager(temp_dir):
    return DailyLogManager(memory_dir=temp_dir)

def test_append_creates_daily_file(manager, temp_dir):
    """Appending a message pair creates today's daily log file."""
    manager.append(
        session_id="sess_001",
        user_id="user_001",
        human_message="我想去成都",
        ai_message="成都3天行程已规划好",
    )
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = temp_dir / f"{today}.md"
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "## Session: sess_001" in content
    assert "Human: 我想去成都" in content
    assert "AI: 成都3天行程已规划好" in content

def test_append_multiple_sessions_same_day(manager, temp_dir):
    """Multiple sessions append to the same daily file."""
    manager.append("sess_001", "u1", "msg1", "resp1")
    manager.append("sess_002", "u2", "msg2", "resp2")
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = temp_dir / f"{today}.md"
    content = log_file.read_text(encoding="utf-8")
    assert "## Session: sess_001" in content
    assert "## Session: sess_002" in content

def test_read_today_and_yesterday_returns_empty_on_fresh_day(manager, temp_dir):
    """Fresh day returns today's empty header."""
    result = manager.read_today_and_yesterday()
    today = datetime.now().strftime("%Y-%m-%d")
    assert f"# {today}" in result

def test_read_session_across_days(manager, temp_dir):
    """A session spanning multiple days returns all entries."""
    # Manually create two day files with same session
    day1 = temp_dir / "2026-03-27.md"
    day1.write_text("# 2026-03-27\n\n## Session: sess_cross\n[20:00]\nHuman: msg1\nAI: resp1\n")
    day2 = temp_dir / "2026-03-28.md"
    day2.write_text("# 2026-03-28\n\n## Session: sess_cross\n[09:00]\nHuman: msg2\nAI: resp2\n")
    result = manager.read_session("sess_cross")
    assert "msg1" in result
    assert "msg2" in result