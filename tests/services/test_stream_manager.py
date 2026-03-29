import pytest
from app.services.stream_manager import StreamManager, get_stream_manager

def test_singleton():
    sm1 = get_stream_manager()
    sm2 = get_stream_manager()
    assert sm1 is sm2

def test_register_unregister_session():
    sm = get_stream_manager()
    session_id = "test-session-1"
    queue = sm.register_session(session_id)
    assert queue is not None
    sm.unregister_session(session_id)

@pytest.mark.asyncio
async def test_emit_and_get():
    sm = get_stream_manager()
    session_id = "test-session-2"
    sm.register_session(session_id)
    await sm.emit(session_id, "test_event", {"key": "value"})
    result = await sm.get_event(session_id)
    assert "event: test_event" in result
    assert '"key": "value"' in result
    sm.unregister_session(session_id)