"""搜索工具 - 封装 Tavily + 高德地图 API 调用"""
import sys
import os
import json
import asyncio
import subprocess
from typing import Any, Dict, List

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.config import get_settings


def _get_amap_manager():
    """获取高德地图管理器实例（延迟导入，避免循环依赖）"""
    from app.skills.smart_map_guide.scripts.map_manager import MapManager
    settings = get_settings()
    return MapManager(settings.amap_api_key)


def _run_tavily_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """调用 Tavily CLI 脚本，返回 parsed JSON"""
    base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills", "tavily")
    script_path = os.path.join(base_dir, "scripts", "tavily_search.py")

    result = subprocess.run(
        [sys.executable, script_path, "--query", query, "--max-results", str(max_results), "--format", "raw"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        raise Exception(f"Tavily failed: {result.stderr}")
    return json.loads(result.stdout)


async def tavily_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Tavily 通用搜索"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_tavily_search, query, max_results)


async def amap_attractions(city: str, page_size: int = 20) -> List[Dict[str, Any]]:
    """高德地图景点 POI 搜索（风景名胜 + 博物馆）"""
    manager = _get_amap_manager()
    result = manager.search_attractions(city=city, page_size=page_size)
    pois = result.get("pois", [])
    return [
        {
            "id": p.get("id", ""),
            "name": p.get("name", ""),
            "city": city,
            "score": 4.5,  # 高德无评分，用默认
            "best_season": "四季皆宜",
            "price_range": p.get("cost", ""),
            "intensity": "medium",
            "tips": p.get("address", ""),
            "location": p.get("location", ""),
            "address": p.get("address", ""),
        }
        for p in pois
    ]


async def amap_restaurants(city: str, page_size: int = 20) -> List[Dict[str, Any]]:
    """高德地图餐厅 POI 搜索（中餐厅 + 外国餐厅）"""
    manager = _get_amap_manager()
    result = manager.search_restaurants(city=city, page_size=page_size)
    pois = result.get("pois", [])
    return [
        {
            "name": p.get("name", ""),
            "cuisine": p.get("type", ""),
            "price_level": p.get("cost", ""),
            "location": p.get("address", ""),
            "avg_budget": 100.0,
        }
        for p in pois
    ]


async def amap_hotels(city: str, budget: float = 500.0, page_size: int = 20) -> List[Dict[str, Any]]:
    """高德地图酒店 POI 搜索（住宿服务）"""
    manager = _get_amap_manager()
    result = manager.search_poi(keywords="酒店", city=city, types="100000", page_size=page_size)
    pois = result.get("pois", [])
    hotels = []
    for p in pois:
        try:
            price = float(p.get("cost", 0))
        except (ValueError, TypeError):
            price = 0
        if budget <= 0 or price <= budget:
            hotels.append({
                "name": p.get("name", ""),
                "location": p.get("address", ""),
                "price_per_night": price,
                "rating": 4.5,
                "nearby_attractions": [],
                "amenities": [],
            })
    return hotels


async def amap_route(from_location: str, to_location: str, city: str, transport: str = "driving") -> Dict[str, Any]:
    """高德地图路线规划

    Args:
        from_location: 起点地址
        to_location: 终点地址
        city: 城市名称
        transport: 交通方式 ("driving" | "walking" | "transit")

    Returns:
        {"distance_km": float, "duration_min": int, "origin": str, "destination": str}
    """
    manager = _get_amap_manager()

    # 获取城市编码
    city_code_map = {"北京": "010", "上海": "021", "广州": "020", "深圳": "0755", "杭州": "0571", "成都": "028"}
    city_code = city_code_map.get(city, "")

    if transport == "driving":
        raw = manager.driving_route(origin=from_location, destination=to_location, origin_city=city, dest_city=city)
        path = raw.get("route", {}).get("paths", [{}])[0]
        cost = path.get("cost", {})
        return {
            "distance_km": float(path.get("distance", 0)) / 1000,
            "duration_min": int(cost.get("duration", 0)) // 60,
            "origin": raw.get("origin_name", from_location),
            "destination": raw.get("dest_name", to_location),
            "tolls": cost.get("tolls", "0"),
        }
    elif transport == "walking":
        raw = manager.walking_route(origin=from_location, destination=to_location, origin_city=city, dest_city=city)
        path = raw.get("route", {}).get("paths", [{}])[0]
        cost = path.get("cost", {})
        return {
            "distance_km": float(path.get("distance", 0)) / 1000,
            "duration_min": int(cost.get("duration", 0)) // 60,
            "origin": raw.get("origin_name", from_location),
            "destination": raw.get("dest_name", to_location),
        }
    elif transport == "transit":
        raw = manager.transit_route(origin=from_location, destination=to_location, city1=city_code, city2=city_code)
        transit = raw.get("route", {}).get("transits", [{}])[0]
        cost = transit.get("cost", {})
        return {
            "distance_km": float(transit.get("distance", 0)) / 1000,
            "duration_min": int(cost.get("duration", 0)) // 60,
            "origin": raw.get("origin_name", from_location),
            "destination": raw.get("dest_name", to_location),
            "transit_fee": cost.get("transit_fee", "0"),
        }
    else:
        raise ValueError(f"Unknown transport type: {transport}")
