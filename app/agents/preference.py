# app/agents/preference.py
"""Preference Agent - manages user preferences in long-term memory.

This is the ONLY agent that writes to long-term memory.
"""
from typing import Any, Dict
from app.tools import preference_tools as pt

class PreferenceAgent:
    """Agent responsible for reading and writing user preferences.

    This agent is the sole writer to long-term SQLite memory.
    Other agents call get_preference() to read but cannot write.
    """

    async def update_preference(self, user_id: str, category: str, value: Any) -> Dict[str, bool]:
        """Update a single preference category for a user."""
        return await pt.update_preference(user_id, category, value)

    async def get_preference(self, user_id: str) -> Dict[str, Any]:
        """Get all preferences for a user (assembled nested dict)."""
        return await pt.get_preference(user_id)

    async def parse_and_update(self, user_id: str, message: str) -> Dict[str, Any]:
        """Parse a user message for preference hints and update memory.

        Looks for patterns like:
        - "我不喜欢硬座" → hardships
        - "我有心脏病" / "糖尿病" → health
        - "我想节省一点" → spending_style = "节省"
        """
        import re
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