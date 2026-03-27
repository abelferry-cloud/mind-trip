# app/tools/attractions_tools.py
"""景点工具 - 搜索和获取旅游景点详情。
使用硬编码的模拟数据集用于演示目的。
"""
from typing import List, Dict, Any

# 模拟数据集
_MOCK_ATTRACTIONS = {
    "attr_hz_001": {
        "id": "attr_hz_001", "name": "西湖", "city": "杭州", "score": 4.8,
        "best_season": "四季皆宜", "price_range": "0-50", "intensity": "low",
        "tips": "建议清晨或傍晚游览，避开人流高峰",
        "open_hours": "全天开放", "ticket_price": 0, "booking_difficulty": "无需预约"
    },
    "attr_hz_002": {
        "id": "attr_hz_002", "name": "灵隐寺", "city": "杭州", "score": 4.7,
        "best_season": "春秋", "price_range": "50-100", "intensity": "medium",
        "tips": "寺庙内请保持安静，注意着装",
        "open_hours": "07:00-18:00", "ticket_price": 75, "booking_difficulty": "建议提前预约"
    },
    "attr_hz_003": {
        "id": "attr_hz_003", "name": "宋城", "city": "杭州", "score": 4.5,
        "best_season": "全年", "price_range": "200-300", "intensity": "high",
        "tips": "《宋城千古情》是必看演出，建议提前购票",
        "open_hours": "09:00-21:00", "ticket_price": 280, "booking_difficulty": "需提前购票"
    },
    "attr_cd_001": {
        "id": "attr_cd_001", "name": "大熊猫繁育研究基地", "city": "成都", "score": 4.9,
        "best_season": "全年", "price_range": "50-100", "intensity": "low",
        "tips": "建议上午前往，熊猫下午多在休息",
        "open_hours": "07:30-18:00", "ticket_price": 55, "booking_difficulty": "建议提前预约"
    },
    "attr_cd_002": {
        "id": "attr_cd_002", "name": "宽窄巷子", "city": "成都", "score": 4.6,
        "best_season": "四季皆宜", "price_range": "0-50", "intensity": "low",
        "tips": "夜晚灯光璀璨，适合拍照",
        "open_hours": "全天开放", "ticket_price": 0, "booking_difficulty": "无需预约"
    },
}

def _match_city(city: str) -> List[Dict[str, Any]]:
    """返回匹配城市的景点（不区分大小写的前缀匹配）。"""
    city_lower = city.lower()
    return [
        {k: v for k, v in attr.items() if k != "open_hours" and k != "ticket_price" and k != "booking_difficulty"}
        for attr in _MOCK_ATTRACTIONS.values()
        if city_lower in attr["city"].lower()
    ]

async def search_attractions(city: str, days: int, season: str) -> List[Dict[str, Any]]:
    """搜索城市的景点。

    返回包含以下字段的景点列表：id, name, score, best_season, price_range, intensity, tips。
    """
    return _match_city(city)

async def get_attraction_detail(attraction_id: str) -> Dict[str, Any]:
    """获取特定景点的详细信息。"""
    attr = _MOCK_ATTRACTIONS.get(attraction_id, {})
    if not attr:
        return {"error": "Attraction not found"}
    return {
        "id": attr["id"], "name": attr["name"],
        "open_hours": attr["open_hours"],
        "ticket_price": attr["ticket_price"],
        "booking_difficulty": attr["booking_difficulty"],
        "intensity": attr["intensity"]
    }

async def check_availability(attraction_id: str, date: str) -> Dict[str, Any]:
    """检查特定景点在特定日期的可用性。

    注意：这返回模拟数据用于演示。实际实现会调用外部 API。
    """
    attr = _MOCK_ATTRACTIONS.get(attraction_id)
    if not attr:
        return {"available": False, "booking_tips": "景点不存在", "crowd_level": "未知"}

    booking_diff = attr.get("booking_difficulty", "")
    if "无需预约" in booking_diff:
        return {"available": True, "booking_tips": "无需预约，可直接前往", "crowd_level": "中等"}
    elif "建议提前预约" in booking_diff:
        return {"available": True, "booking_tips": "建议提前2天预约", "crowd_level": "较高"}
    else:
        return {"available": True, "booking_tips": "需提前购票，建议提前1周", "crowd_level": "高"}