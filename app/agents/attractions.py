# app/agents/attractions.py
"""景点 Agent - 根据用户偏好搜索和筛选景点。"""
from typing import Dict, Any, List
from app.tools import attractions_tools as at

class AttractionsAgent:
    """景点搜索和筛选专家 Agent。

    从偏好 Agent 读取偏好，过滤不合适的景点
    （例如：心脏病患者不适合高强度活动）。
    """

    async def search(self, city: str, days: int, season: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """搜索景点并根据用户偏好筛选。"""
        attractions = await at.search_attractions(city, days, season)

        # 根据健康偏好筛选
        health_prefs = preferences.get("health", [])
        mobility_limitations = []
        if any(h in health_prefs for h in ["心脏病", "高血压", "哮喘"]):
            mobility_limitations.append("high_intensity")

        filtered = attractions
        if mobility_limitations:
            filtered = [a for a in attractions if a.get("intensity") != "high"]

        return {"attractions": filtered, "city": city, "days": days}

    async def get_detail(self, attraction_id: str) -> Dict[str, Any]:
        return await at.get_attraction_detail(attraction_id)

    async def check_availability(self, attraction_id: str, date: str) -> Dict[str, Any]:
        return await at.check_availability(attraction_id, date)
