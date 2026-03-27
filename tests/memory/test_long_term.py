import pytest, asyncio
from app.memory.long_term import LongTermMemory, get_long_term_memory

@pytest.fixture
def mem():
    return get_long_term_memory(":memory:")

@pytest.mark.asyncio
async def test_update_and_get_preference(mem):
    await mem.update_preference("u1", "hardships", ["硬座"])
    await mem.update_preference("u1", "health", ["心脏病"])

    prefs = await mem.get_preference("u1")
    assert prefs["hardships"] == ["硬座"]
    assert prefs["health"] == ["心脏病"]

@pytest.mark.asyncio
async def test_update_overwrites(mem):
    await mem.update_preference("u1", "health", ["心脏病"])
    await mem.update_preference("u1", "health", ["糖尿病"])
    prefs = await mem.get_preference("u1")
    assert prefs["health"] == ["糖尿病"]

@pytest.mark.asyncio
async def test_trip_history(mem):
    plan = {"city": "杭州", "days": 3, "budget": 5000}
    await mem.save_trip_history("u1", "杭州", 3, plan)
    history = await mem.get_trip_history("u1")
    assert len(history) == 1
    assert history[0]["city"] == "杭州"