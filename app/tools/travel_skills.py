"""Travel Skills - 封装 Tavily + 高德地图为 LangChain Tool

提供带错误处理、重试机制和缓存的标准化工具函数。
"""
import time
from typing import Annotated, List

from langchain_core.tools import tool

from app.tools.base import ToolResult, ToolException, ToolErrorCategory
from app.tools.decorators import retry, cached

# 导入地图管理器和搜索模块
from app.skills.smart_map_guide.scripts.map_manager import MapManager
from app.skills.tavily.scripts.tavily_search import tavily_search

# 全局地图管理器实例
_map_manager: MapManager | None = None


def get_map_manager() -> MapManager:
    """获取地图管理器单例"""
    global _map_manager
    if _map_manager is None:
        from app.config import get_settings
        settings = get_settings()
        _map_manager = MapManager(settings.amap_api_key)
    return _map_manager


def _handle_api_error(func_name: str, error: Exception) -> ToolException:
    """将 API 错误转换为 ToolException

    根据错误类型分类：
    - 超时错误：标记为可重试
    - 网络错误：标记为可重试
    - 其他 API 错误：不可重试
    """
    error_msg = str(error)
    if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
        return ToolException(
            category=ToolErrorCategory.TIMEOUT_ERROR,
            message=f"{func_name} 请求超时: {error_msg}",
            retryable=True
        )
    elif "network" in error_msg.lower() or "connection" in error_msg.lower():
        return ToolException(
            category=ToolErrorCategory.NETWORK_ERROR,
            message=f"{func_name} 网络错误: {error_msg}",
            retryable=True
        )
    else:
        return ToolException(
            category=ToolErrorCategory.API_ERROR,
            message=f"{func_name} API 错误: {error_msg}",
            retryable=False
        )


def _infer_intensity(name: str, ptype: str) -> str:
    """根据名称和类型推断体力消耗强度"""
    high_keywords = ["登山", "徒步", "攀岩", "探险", "极限"]
    medium_keywords = ["观光", "博物馆", "寺庙", "古镇"]
    if any(k in name for k in high_keywords) or "high" in ptype.lower():
        return "high"
    if any(k in name for k in medium_keywords):
        return "medium"
    return "low"


@tool
@cached(ttl=300)  # 5分钟缓存
@retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(Exception,))
def search_attractions(city: Annotated[str, "城市名称"]) -> ToolResult:
    """搜索城市景点（风景名胜 + 博物馆）

    缓存策略：5分钟 TTL
    重试策略：最多3次，指数退避
    """
    start_time = time.time()
    mgr = get_map_manager()
    result = mgr.search_attractions(city, page_size=20)
    pois = result.get("pois", [])
    data = [
        {
            "name": p.get("name", ""),
            "address": p.get("address", ""),
            "type": p.get("type", ""),
            "location": p.get("location", ""),
            "intensity": _infer_intensity(p.get("name", ""), p.get("type", "")),
        }
        for p in pois
    ]
    duration_ms = int((time.time() - start_time) * 1000)
    return ToolResult(
        success=True,
        data=data,
        metadata={"tool_name": "search_attractions", "cached": False, "duration_ms": duration_ms}
    )


@tool
@cached(ttl=300)  # 5分钟缓存
@retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(Exception,))
def search_restaurants(
    city: Annotated[str, "城市名称"],
    cuisine: Annotated[str, "菜系类型（可选）"] = "",
) -> ToolResult:
    """搜索城市餐厅（排除快餐）

    缓存策略：5分钟 TTL
    重试策略：最多3次，指数退避
    """
    start_time = time.time()
    try:
        mgr = get_map_manager()
        result = mgr.search_restaurants(city, page_size=20)
        pois = result.get("pois", [])
        if cuisine:
            pois = [p for p in pois if cuisine in p.get("type", "")]
        data = [
            {
                "name": p.get("name", ""),
                "address": p.get("address", ""),
                "type": p.get("type", ""),
                "location": p.get("location", ""),
            }
            for p in pois
        ]
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolResult(
            success=True,
            data=data,
            metadata={"tool_name": "search_restaurants", "cached": False, "duration_ms": duration_ms}
        )
    except Exception as e:
        exc = _handle_api_error("search_restaurants", e)
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolResult(
            success=False,
            error=exc,
            metadata={"tool_name": "search_restaurants", "duration_ms": duration_ms}
        )


@tool
@cached(ttl=300)  # 5分钟缓存
@retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(Exception,))
def search_hotels(
    city: Annotated[str, "城市名称"],
    budget: Annotated[float, "每晚预算"] = 500.0,
    location: Annotated[str, "位置偏好（可选）"] = "",
) -> ToolResult:
    """搜索城市酒店

    缓存策略：5分钟 TTL
    重试策略：最多3次，指数退避
    """
    start_time = time.time()
    try:
        mgr = get_map_manager()
        result = mgr.search_poi(keywords="酒店", city=city, types="100000", page_size=20)
        pois = result.get("pois", [])
        if location:
            pois = [p for p in pois if location in p.get("address", "")]
        data = [
            {
                "name": p.get("name", ""),
                "address": p.get("address", ""),
                "location": p.get("location", ""),
            }
            for p in pois
        ]
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolResult(
            success=True,
            data=data,
            metadata={"tool_name": "search_hotels", "cached": False, "duration_ms": duration_ms}
        )
    except Exception as e:
        exc = _handle_api_error("search_hotels", e)
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolResult(
            success=False,
            error=exc,
            metadata={"tool_name": "search_hotels", "duration_ms": duration_ms}
        )


@tool
# 不缓存 - 路线规划需要实时数据
@retry(max_attempts=2, delay=1.0, backoff=2.0, exceptions=(Exception,))
def plan_driving_route(
    origin: Annotated[str, "起点地址或坐标"],
    destination: Annotated[str, "终点地址或坐标"],
    city: Annotated[str, "城市名称（用于地理编码）"] = "",
) -> ToolResult:
    """驾车路线规划（高德地图）

    重试策略：最多3次，指数退避
    缓存策略：不缓存
    """
    start_time = time.time()
    try:
        mgr = get_map_manager()
        result = mgr.driving_route(origin, destination, origin_city=city, dest_city=city)
        path = result["route"]["paths"][0]
        data = {
            "distance_km": round(float(path.get("distance", 0)) / 1000, 1),
            "duration_min": int(int(path["cost"]["duration"]) / 60),
            "tolls": path["cost"].get("tolls", "0"),
            "origin_name": result.get("origin_name", origin),
            "dest_name": result.get("dest_name", destination),
        }
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolResult(
            success=True,
            data=data,
            metadata={"tool_name": "plan_driving_route", "duration_ms": duration_ms}
        )
    except Exception as e:
        exc = _handle_api_error("plan_driving_route", e)
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolResult(
            success=False,
            error=exc,
            metadata={"tool_name": "plan_driving_route", "duration_ms": duration_ms}
        )


@tool
# 不缓存 - 路线规划需要实时数据
@retry(max_attempts=2, delay=1.0, backoff=2.0, exceptions=(Exception,))
def plan_walking_route(
    origin: Annotated[str, "起点地址或坐标"],
    destination: Annotated[str, "终点地址或坐标"],
    city: Annotated[str, "城市名称"] = "",
) -> ToolResult:
    """步行路线规划（高德地图）

    重试策略：最多3次，指数退避
    缓存策略：不缓存
    """
    start_time = time.time()
    try:
        mgr = get_map_manager()
        result = mgr.walking_route(origin, destination, origin_city=city, dest_city=city)
        path = result["route"]["paths"][0]
        data = {
            "distance_km": round(float(path.get("distance", 0)) / 1000, 1),
            "duration_min": int(int(path["cost"]["duration"]) / 60),
        }
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolResult(
            success=True,
            data=data,
            metadata={"tool_name": "plan_walking_route", "duration_ms": duration_ms}
        )
    except Exception as e:
        exc = _handle_api_error("plan_walking_route", e)
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolResult(
            success=False,
            error=exc,
            metadata={"tool_name": "plan_walking_route", "duration_ms": duration_ms}
        )


@tool
@cached(ttl=900)  # 15分钟缓存
@retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(Exception,))
def tavily_web_search(
    query: Annotated[str, "搜索查询"],
    max_results: Annotated[int, "最大结果数"] = 5,
) -> ToolResult:
    """Tavily 网络搜索（用于补充实时信息）

    缓存策略：15分钟 TTL
    重试策略：最多3次，指数退避
    """
    start_time = time.time()
    try:
        result = tavily_search(
            query=query,
            max_results=max_results,
            include_answer=False,
            search_depth="basic",
        )
        data = {
            "results": result.get("results", []),
            "answer": result.get("answer"),
        }
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolResult(
            success=True,
            data=data,
            metadata={"tool_name": "tavily_web_search", "cached": False, "duration_ms": duration_ms}
        )
    except Exception as e:
        exc = _handle_api_error("tavily_web_search", e)
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolResult(
            success=False,
            error=exc,
            metadata={"tool_name": "tavily_web_search", "duration_ms": duration_ms}
        )
