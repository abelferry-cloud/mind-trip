# tests/tools/test_hotel_tools.py
import pytest
from app.tools.hotel_tools import search_hotels

@pytest.mark.asyncio
async def test_search_hotels_returns_list():
    results = await search_hotels("杭州", 300.0, "西湖区")
    assert isinstance(results, list)
    assert len(results) > 0
    assert "name" in results[0]
    assert "price" in results[0]