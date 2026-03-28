import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.agents.preference import PreferenceAgent


@pytest.mark.asyncio
async def test_parse_and_update_health_keywords():
    """Health keywords in message trigger health preference update."""
    with patch('app.agents.preference.get_markdown_memory_manager') as mock_get:
        mock_mgr = MagicMock()
        mock_mgr.update_preference = AsyncMock()
        mock_get.return_value = mock_mgr

        agent = PreferenceAgent()
        result = await agent.parse_and_update("user_001", "我有心脏病和糖尿病")

        # Should have triggered 2 health updates
        calls = mock_mgr.update_preference.call_args_list
        categories = [call[0][1] for call in calls]  # [0] is args, [1] is category
        assert "health" in categories
        assert result["updated"]  # non-empty


@pytest.mark.asyncio
async def test_parse_and_update_spending_style():
    """Spending keywords trigger spending_style update."""
    with patch('app.agents.preference.get_markdown_memory_manager') as mock_get:
        mock_mgr = MagicMock()
        mock_mgr.update_preference = AsyncMock()
        mock_get.return_value = mock_mgr

        agent = PreferenceAgent()
        result = await agent.parse_and_update("user_001", "我想节省一点")

        calls = mock_mgr.update_preference.call_args_list
        categories = [call[0][1] for call in calls]
        assert "spending_style" in categories
        assert result["updated"]
