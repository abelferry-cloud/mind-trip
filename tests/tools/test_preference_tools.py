import pytest
from unittest.mock import AsyncMock, patch
from app.tools.preference_tools import update_preference, get_preference

@pytest.mark.asyncio
async def test_update_preference():
    mock_mem = AsyncMock()
    mock_mem.update_preference = AsyncMock()
    with patch("app.tools.preference_tools.get_long_term_memory", return_value=mock_mem):
        result = await update_preference("u1", "hardships", ["硬座"])
        assert result["success"] is True
        mock_mem.update_preference.assert_called_once_with("u1", "hardships", ["硬座"])

@pytest.mark.asyncio
async def test_get_preference():
    mock_mem = AsyncMock()
    mock_mem.get_preference = AsyncMock(return_value={"hardships": ["硬座"], "health": ["心脏病"]})
    with patch("app.tools.preference_tools.get_long_term_memory", return_value=mock_mem):
        result = await get_preference("u1")
        assert result["hardships"] == ["硬座"]
        assert result["health"] == ["心脏病"]