"""Preference Tools - read/write user preferences to long-term memory."""
from typing import Any, Dict
from app.memory.long_term import get_long_term_memory

async def update_preference(user_id: str, category: str, value: Any) -> Dict[str, bool]:
    """Update a user preference in long-term memory.

    Args:
        user_id: User identifier
        category: Preference category (hardships/health/spending_style/city_preferences)
        value: Preference value (list or string)

    Returns:
        {"success": true}
    """
    mem = get_long_term_memory()
    await mem.update_preference(user_id, category, value)
    return {"success": True}

async def get_preference(user_id: str) -> Dict[str, Any]:
    """Get all preferences for a user, assembled as nested dict.

    Returns:
        {"hardships": [...], "health": [...], "spending_style": "...", ...}
    """
    mem = get_long_term_memory()
    return await mem.get_preference(user_id)