# app/agents/preference.py
"""偏好 Agent - 管理长期记忆中的用户偏好。

这是唯一可以写入长期记忆的 Agent。
"""
from typing import Any, Dict
from app.tools import preference_tools as pt

class PreferenceAgent:
    """负责读写用户偏好的 Agent。

    该 Agent 是唯一可以写入长期 SQLite 记忆的 Agent。
    其他 Agent 调用 get_preference() 读取但不能写入。
    """

    async def update_preference(self, user_id: str, category: str, value: Any) -> Dict[str, bool]:
        """更新用户的单个偏好类别。"""
        return await pt.update_preference(user_id, category, value)

    async def get_preference(self, user_id: str) -> Dict[str, Any]:
        """获取用户的所有偏好（组装成嵌套字典）。"""
        return await pt.get_preference(user_id)

    async def parse_and_update(self, user_id: str, message: str) -> Dict[str, Any]:
        """解析用户消息中的偏好提示并更新记忆。

        查找如下模式：
        - "我不喜欢硬座" → hardships
        - "我有心脏病" / "糖尿病" → health
        - "我想节省一点" → spending_style = "节省"
        """
        import re
        updates = []

        # 健康状况
        health_keywords = ["心脏病", "糖尿病", "高血压", "哮喘", "过敏", "癫痫"]
        for kw in health_keywords:
            if kw in message:
                await self.update_preference(user_id, "health", [kw])
                updates.append(kw)

        # 艰苦条件
        hardship_keywords = ["硬座", "红眼航班", "转机", "步行", "爬山"]
        for kw in hardship_keywords:
            if kw in message:
                await self.update_preference(user_id, "hardships", [kw])
                updates.append(kw)

        # 消费风格
        if "节省" in message or "省钱" in message:
            await self.update_preference(user_id, "spending_style", "节省")
            updates.append("spending_style=节省")
        elif "奢侈" in message or "豪华" in message:
            await self.update_preference(user_id, "spending_style", "奢侈")
            updates.append("spending_style=奢侈")

        return {"updated": updates}