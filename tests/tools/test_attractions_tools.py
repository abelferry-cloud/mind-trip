# tests/tools/test_attractions_tools.py
import pytest
from app.tools.attractions_tools import search_attractions, get_attraction_detail, check_availability

@pytest.mark.asyncio
async def test_search_attractions_returns_list():
    results = await search_attractions("杭州", 3, "spring")
    assert isinstance(results, list)
    assert len(results) > 0
    assert "name" in results[0]
    assert "intensity" in results[0]

@pytest.mark.asyncio
async def test_get_attraction_detail():
    results = await search_attractions("杭州", 3, "spring")
    attr_id = results[0]["id"]
    detail = await get_attraction_detail(attr_id)
    assert detail["id"] == attr_id
    assert "open_hours" in detail

@pytest.mark.asyncio
async def test_check_availability():
    results = await search_attractions("杭州", 3, "spring")
    attr_id = results[0]["id"]
    avail = await check_availability(attr_id, "2026-04-01")
    assert "available" in avail
    assert "booking_tips" in avail