"""偏好工具 - 读写用户偏好到长期记忆。"""
from typing import Any, Dict
from app.memory.long_term import get_long_term_memory

async def update_preference(user_id: str, category: str, value: Any) -> Dict[str, bool]:
    """更新长期记忆中的用户偏好。

    Args:
        user_id: 用户标识符
        category: 偏好类别（hardships/health/spending_style/city_preferences）
        value: 偏好值（列表或字符串）

    Returns:
        {"success": true}
    """
    mem = get_long_term_memory()
    await mem.update_preference(user_id, category, value)
    return {"success": True}

async def get_preference(user_id: str) -> Dict[str, Any]:
    """获取用户的所有偏好，组装为嵌套字典。

    Returns:
        {"hardships": [...], "health": [...], "spending_style": "...", ...}
    """
    mem = get_long_term_memory()
    return await mem.get_preference(user_id)