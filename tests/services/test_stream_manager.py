import pytest
from app.services.stream_manager import StreamManager, get_stream_manager

@pytest.mark.asyncio
async def test_singleton():
    sm1 = await get_stream_manager()
    sm2 = await get_stream_manager()
    assert sm1 is sm2

@pytest.mark.asyncio
async def test_register_unregister_session():
    sm = await get_stream_manager()
    session_id = "test-session-1"
    queue = sm.register_session(session_id)
    # Verify queue can hold and retrieve an item
    await queue.put("test_item")
    retrieved = await queue.get()
    assert retrieved == "test_item"
    sm.unregister_session(session_id)
    # After unregister_session, get_event returns None for that session
    result = await sm.get_event(session_id)
    assert result is None

@pytest.mark.asyncio
async def test_emit_and_get():
    sm = await get_stream_manager()
    session_id = "test-session-2"
    sm.register_session(session_id)
    await sm.emit(session_id, "test_event", {"key": "value"})
    result = await sm.get_event(session_id)
    assert "event: test_event" in result
    assert '"key": "value"' in result
    sm.unregister_session(session_id)