# app/tools/food_tools.py
"""Food Tools - recommend local restaurants.
Mock dataset for demonstration.
"""
from typing import List, Dict, Any

_MOCK_RESTAURANTS = {
    "杭州": [
        {"name": "外婆家", "cuisine": "浙菜", "price_level": "¥", "location": "西湖区",
         "signature_dishes": ["东坡肉", "叫化鸡", "西湖醋鱼"], "avg_budget": 80},
        {"name": "知味观", "cuisine": "浙菜/小吃", "price_level": "¥¥", "location": "西湖区",
         "signature_dishes": ["小笼包", "片儿川"], "avg_budget": 120},
        {"name": "楼外楼", "cuisine": "浙菜", "price_level": "¥¥¥", "location": "西湖",
         "signature_dishes": ["东坡肉", "宋嫂鱼羹"], "avg_budget": 250},
    ],
    "成都": [
        {"name": "玉林串串香", "cuisine": "川菜/火锅", "price_level": "¥", "location": "武侯区",
         "signature_dishes": ["串串", "冒菜"], "avg_budget": 60},
        {"name": "蜀大侠火锅", "cuisine": "川菜/火锅", "price_level": "¥¥", "location": "锦江区",
         "signature_dishes": ["牛油锅底", "鲜毛肚"], "avg_budget": 120},
        {"name": "陈麻婆豆腐", "cuisine": "川菜", "price_level": "¥¥", "location": "青羊区",
         "signature_dishes": ["麻婆豆腐", "夫妻肺片"], "avg_budget": 100},
    ],
}

async def recommend_restaurants(city: str, style: str = "", budget_per_meal: float = 100.0) -> List[Dict[str, Any]]:
    """Recommend restaurants in a city.

    Args:
        city: City name
        style: Cuisine preference (e.g., "浙菜", empty = all)
        budget_per_meal: Budget per meal in CNY

    Returns:
        List of restaurant dicts
    """
    restaurants = _MOCK_RESTAURANTS.get(city, [])
    if style:
        restaurants = [r for r in restaurants if style in r["cuisine"] or not style]
    # Filter by budget
    restaurants = [r for r in restaurants if r["avg_budget"] <= budget_per_meal * 1.5]
    return restaurants