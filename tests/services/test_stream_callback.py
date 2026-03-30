import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.stream_callback import StreamCallbackHandler


@pytest.fixture
def mock_stream_manager():
    manager = MagicMock()
    manager.emit = AsyncMock()
    manager.tool_start = AsyncMock()
    manager.tool_end = AsyncMock()
    manager.reasoning_step = AsyncMock()
    manager.iteration = AsyncMock()
    return manager


@pytest.fixture
def handler(mock_stream_manager):
    return StreamCallbackHandler(mock_stream_manager, "test_session")


@pytest.mark.asyncio
async def test_on_llm_new_token(handler, mock_stream_manager):
    await handler.on_llm_new_token("你")
    mock_stream_manager.emit.assert_called_once_with(
        "test_session",
        "llm_new_token",
        {"token": "你"}
    )


@pytest.mark.asyncio
async def test_on_tool_end_summarizes_list_result(handler, mock_stream_manager):
    result = {"items": [{"name": "景点1"}, {"name": "景点2"}]}
    await handler.on_tool_end("search_attractions", result, 120)
    mock_stream_manager.tool_end.assert_called_once_with(
        "test_session",
        "search_attractions",
        "找到 2 个结果",
        120,
    )
