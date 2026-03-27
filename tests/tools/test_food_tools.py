# tests/tools/test_food_tools.py
import pytest
from app.tools.food_tools import recommend_restaurants

@pytest.mark.asyncio
async def test_recommend_returns_list():
    results = await recommend_restaurants("杭州", "浙菜", 100.0)
    assert isinstance(results, list)
    assert len(results) > 0
    assert "name" in results[0]
    assert "cuisine" in results[0]