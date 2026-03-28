# app/agents/preference.py
"""偏好 Agent - 管理长期记忆中的用户偏好 (Markdown 版本).

这是唯一可以写入长期记忆的 Agent。
写入目标：MEMORY.md（长期）+ memory/YYYY-MM-DD.md（每日）
"""
from typing import Any, Dict
from app.memory.markdown_memory import MarkdownMemoryManager


class PreferenceAgent:
    """负责读写用户偏好的 Agent (Markdown 版本).

    该 Agent 是唯一可以写入长期 Markdown 记忆的 Agent。
    其他 Agent 调用 get_preference() 读取但不能写入。
    """

    def __init__(self):
        self._memory_mgr: MarkdownMemoryManager = get_markdown_memory_manager()

    async def update_preference(self, user_id: str, category: str, value: Any) -> Dict[str, bool]:
        """更新用户的单个偏好类别到 MEMORY.md。"""
        await self._memory_mgr.update_preference(user_id, category, value)
        return {"success": True}

    async def get_preference(self, user_id: str) -> Dict[str, Any]:
        """获取用户的所有偏好（从 MEMORY.md 读取）。

        Returns:
            偏好字典，按 category 组织。
        """
        content = self._memory_mgr.get_memory()
        import re
        prefs = {}
        m = re.search(r"- \*\*Spending Style\*\*: (.+?)\n", content)
        if m:
            prefs["spending_style"] = m.group(1).strip()
        return prefs

    async def parse_and_update(self, user_id: str, message: str) -> Dict[str, Any]:
        """解析用户消息中的偏好提示并更新记忆。

        查找如下模式：
        - "我不喜欢硬座" → hardships
        - "我有心脏病" / "糖尿病" → health
        - "我想节省一点" → spending_style = "节省"
        """
        updates = []

        # Health conditions
        health_keywords = ["心脏病", "糖尿病", "高血压", "哮喘", "过敏", "癫痫"]
        for kw in health_keywords:
            if kw in message:
                await self.update_preference(user_id, "health", [kw])
                updates.append(kw)

        # Hardships
        hardship_keywords = ["硬座", "红眼航班", "转机", "步行", "爬山"]
        for kw in hardship_keywords:
            if kw in message:
                await self.update_preference(user_id, "hardships", [kw])
                updates.append(kw)

        # Spending style
        if "节省" in message or "省钱" in message:
            await self.update_preference(user_id, "spending_style", "节省")
            updates.append("spending_style=节省")
        elif "奢侈" in message or "豪华" in message:
            await self.update_preference(user_id, "spending_style", "奢侈")
            updates.append("spending_style=奢侈")

        return {"updated": updates}


# Singleton factory
_memory_mgr_instance: MarkdownMemoryManager | None = None


def get_markdown_memory_manager() -> MarkdownMemoryManager:
    global _memory_mgr_instance
    if _memory_mgr_instance is None:
        _memory_mgr_instance = MarkdownMemoryManager()
    return _memory_mgr_instance
