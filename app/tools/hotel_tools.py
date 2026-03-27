# app/tools/hotel_tools.py
"""酒店工具 - 搜索和推荐酒店。
模拟数据集用于演示。
"""
from typing import List, Dict, Any

_MOCK_HOTELS = {
    "杭州": [
        {"name": "如家精选（西湖断桥店）", "location": "西湖区", "price_per_night": 280,
         "rating": 4.5, "nearby_attractions": ["西湖", "断桥"], "amenities": ["WiFi", "早餐"]},
        {"name": "杭州香格里拉饭店", "location": "西湖区", "price_per_night": 680,
         "rating": 4.8, "nearby_attractions": ["西湖", "音乐喷泉"], "amenities": ["WiFi", "健身房", "早餐"]},
        {"name": "汉庭酒店（西湖店）", "location": "西湖区", "price_per_night": 180,
         "rating": 4.2, "nearby_attractions": ["西湖"], "amenities": ["WiFi"]},
    ],
    "成都": [
        {"name": "成都熊猫慢旅酒店", "location": "成华区", "price_per_night": 250,
         "rating": 4.6, "nearby_attractions": ["大熊猫基地", "宽窄巷子"], "amenities": ["WiFi", "早餐"]},
        {"name": "成都瑞吉酒店", "location": "锦江区", "price_per_night": 900,
         "rating": 4.9, "nearby_attractions": ["春熙路", "太古里"], "amenities": ["WiFi", "健身房", "泳池"]},
    ],
}

async def search_hotels(city: str, budget: float = 500.0, location_preference: str = "") -> List[Dict[str, Any]]:
    """搜索城市的酒店，在预算范围内。

    Args:
        city: 城市名
        budget: 每晚最高价格（CNY）
        location_preference: 偏好区域（空=任意）

    Returns:
        酒店列表
    """
    hotels = _MOCK_HOTELS.get(city, [])
    if budget:
        hotels = [h for h in hotels if h["price_per_night"] <= budget]
    if location_preference:
        hotels = [h for h in hotels if location_preference in h["location"]]
    return hotels