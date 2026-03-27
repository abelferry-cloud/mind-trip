# app/services/memory_service.py
"""Memory Service - unified access to long-term memory with write permission control.

Per design Section 3.3: Only Preference Agent can write to long-term memory.
Other agents get read-only access. This is enforced by role check, not technically.
"""
from typing import Optional, Dict, Any, List
from app.memory.long_term import get_long_term_memory, LongTermMemory

_WRITE_ENABLED_AGENTS = {"PreferenceAgent"}

class MemoryService:
    """Service layer wrapping LongTermMemory with permission control."""

    def __init__(self):
        self._mem: Optional[LongTermMemory] = None

    def _get_mem(self) -> LongTermMemory:
        if self._mem is None:
            self._mem = get_long_term_memory()
        return self._mem

    def can_write(self, agent_name: str) -> bool:
        """Check if an agent has write permission to long-term memory."""
        return agent_name in _WRITE_ENABLED_AGENTS

    def can_read(self, agent_name: str) -> bool:
        """All agents can read long-term memory."""
        return True

    # Preference write methods (only PreferenceAgent should call these)
    async def update_preference(self, user_id: str, category: str, value: Any):
        mem = self._get_mem()
        await mem.update_preference(user_id, category, value)

    async def get_preference(self, user_id: str) -> Dict[str, Any]:
        mem = self._get_mem()
        return await mem.get_preference(user_id)

    async def save_trip_history(self, user_id: str, city: str, days: int, plan_summary: dict):
        mem = self._get_mem()
        await mem.save_trip_history(user_id, city, days, plan_summary)

    async def get_trip_history(self, user_id: str) -> List[Dict]:
        mem = self._get_mem()
        return await mem.get_trip_history(user_id)

_svc: Optional[MemoryService] = None

def get_memory_service() -> MemoryService:
    global _svc
    if _svc is None:
        _svc = MemoryService()
    return _svc