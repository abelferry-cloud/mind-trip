"""Travel Skills - 封装 Tavily + 高德地图为 LangChain Tool"""
from typing import Annotated, List
from langchain_core.tools import tool
from app.skills.smart_map_guide.scripts.map_manager import MapManager
from app.skills.tavily.scripts.tavily_search import tavily_search

_map_manager: MapManager | None = None


def get_map_manager() -> MapManager:
    global _map_manager
    if _map_manager is None:
        from app.config import get_settings
        settings = get_settings()
        _map_manager = MapManager(settings.amap_api_key)
    return _map_manager


@tool
def search_attractions(city: Annotated[str, "城市名称"]) -> Annotated[List[dict], "景点列表"]:
    """搜索城市景点（风景名胜 + 博物馆）"""
    mgr = get_map_manager()
    result = mgr.search_attractions(city, page_size=20)
    pois = result.get("pois", [])
    return [
        {
            "name": p.get("name", ""),
            "address": p.get("address", ""),
            "type": p.get("type", ""),
            "location": p.get("location", ""),
            "intensity": _infer_intensity(p.get("name", ""), p.get("type", "")),
        }
        for p in pois
    ]


@tool
def search_restaurants(
    city: Annotated[str, "城市名称"],
    cuisine: Annotated[str, "菜系类型（可选）"] = "",
) -> Annotated[List[dict], "餐厅列表"]:
    """搜索城市餐厅（排除快餐）"""
    mgr = get_map_manager()
    result = mgr.search_restaurants(city, page_size=20)
    pois = result.get("pois", [])
    if cuisine:
        pois = [p for p in pois if cuisine in p.get("type", "")]
    return [
        {
            "name": p.get("name", ""),
            "address": p.get("address", ""),
            "type": p.get("type", ""),
            "location": p.get("location", ""),
        }
        for p in pois
    ]


@tool
def search_hotels(
    city: Annotated[str, "城市名称"],
    budget: Annotated[float, "每晚预算"] = 500.0,
    location: Annotated[str, "位置偏好（可选）"] = "",
) -> Annotated[List[dict], "酒店列表"]:
    """搜索城市酒店"""
    mgr = get_map_manager()
    result = mgr.search_poi(keywords="酒店", city=city, types="100000", page_size=20)
    pois = result.get("pois", [])
    if location:
        pois = [p for p in pois if location in p.get("address", "")]
    return [
        {
            "name": p.get("name", ""),
            "address": p.get("address", ""),
            "location": p.get("location", ""),
        }
        for p in pois
    ]


@tool
def plan_driving_route(
    origin: Annotated[str, "起点地址或坐标"],
    destination: Annotated[str, "终点地址或坐标"],
    city: Annotated[str, "城市名称（用于地理编码）"] = "",
) -> Annotated[dict, "路线规划结果"]:
    """驾车路线规划（高德地图）"""
    mgr = get_map_manager()
    result = mgr.driving_route(origin, destination, origin_city=city, dest_city=city)
    path = result["route"]["paths"][0]
    return {
        "distance_km": round(float(path.get("distance", 0)) / 1000, 1),
        "duration_min": int(int(path["cost"]["duration"]) / 60),
        "tolls": path["cost"].get("tolls", "0"),
        "origin_name": result.get("origin_name", origin),
        "dest_name": result.get("dest_name", destination),
    }


@tool
def plan_walking_route(
    origin: Annotated[str, "起点地址或坐标"],
    destination: Annotated[str, "终点地址或坐标"],
    city: Annotated[str, "城市名称"] = "",
) -> Annotated[dict, "步行路线结果"]:
    """步行路线规划（高德地图）"""
    mgr = get_map_manager()
    result = mgr.walking_route(origin, destination, origin_city=city, dest_city=city)
    path = result["route"]["paths"][0]
    return {
        "distance_km": round(float(path.get("distance", 0)) / 1000, 1),
        "duration_min": int(int(path["cost"]["duration"]) / 60),
    }


@tool
def tavily_web_search(
    query: Annotated[str, "搜索查询"],
    max_results: Annotated[int, "最大结果数"] = 5,
) -> Annotated[dict, "搜索结果"]:
    """Tavily 网络搜索（用于补充实时信息）"""
    result = tavily_search(
        query=query,
        max_results=max_results,
        include_answer=False,
        search_depth="basic",
    )
    return {
        "results": result.get("results", []),
        "answer": result.get("answer"),
    }


def _infer_intensity(name: str, ptype: str) -> str:
    """根据名称和类型推断体力消耗强度"""
    high_keywords = ["登山", "徒步", "攀岩", "探险", "极限"]
    medium_keywords = ["观光", "博物馆", "寺庙", "古镇"]
    if any(k in name for k in high_keywords) or "high" in ptype.lower():
        return "high"
    if any(k in name for k in medium_keywords):
        return "medium"
    return "low"
