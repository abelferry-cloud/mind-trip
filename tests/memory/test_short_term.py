import pytest
from app.memory.short_term import ShortTermMemory, get_short_term_memory

def test_store_and_retrieve():
    mem = get_short_term_memory("session_123")
    mem.save_context({"input": "我要去杭州"}, {"output": "好的，杭州3天"})
    messages = mem.get_messages()
    assert len(messages) == 2

def test_session_isolation():
    mem1 = get_short_term_memory("session_abc")
    mem2 = get_short_term_memory("session_abc")  # Same session_id
    mem1.save_context({"input": "A"}, {"output": "A done"})
    mem2.save_context({"input": "B"}, {"output": "B done"})
    assert len(mem1.get_messages()) == 4  # Same session accumulates
    assert len(mem2.get_messages()) == 4
    assert mem1 is mem2  # same instance for same session_id