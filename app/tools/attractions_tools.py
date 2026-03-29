"""景点工具 - 委托给 travel_skills"""
from typing import List, Dict, Any
from app.tools.travel_skills import search_attractions

async def search_attractions(city: str, days: int, season: str) -> List[Dict[str, Any]]:
    """搜索城市的景点（委托给 travel_skills）"""
    result = search_attractions.invoke({"city": city})
    # 转换格式以保持兼容
    return [
        {
            "id": f"attr_{i}",
            "name": r.get("name", ""),
            "city": city,
            "score": 4.5,
            "best_season": "四季皆宜",
            "price_range": "未知",
            "intensity": r.get("intensity", "medium"),
            "tips": r.get("address", ""),
            "ticket_price": 0,
        }
        for i, r in enumerate(result)
    ]

async def get_attraction_detail(attraction_id: str) -> Dict[str, Any]:
    """获取景点详情（暂不支持）"""
    return {"error": "Not implemented - use Amap POI detail API"}

async def check_availability(attraction_id: str, date: str) -> Dict[str, Any]:
    """检查可用性（暂不支持）"""
    return {"available": True, "booking_tips": "请通过景点官网预约"}
