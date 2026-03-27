# app/services/memory_service.py
"""记忆服务 - 统一访问长期记忆，具有写入权限控制。

根据设计文档第 3.3 节：只有偏好 Agent 可以写入长期记忆。
其他 Agent 只能读取。这通过角色检查强制执行，而非技术限制。
"""
from typing import Optional, Dict, Any, List
from app.memory.long_term import get_long_term_memory, LongTermMemory

_WRITE_ENABLED_AGENTS = {"PreferenceAgent"}

class MemoryService:
    """带有权限控制的 MemoryService 服务层封装。"""

    def __init__(self):
        self._mem: Optional[LongTermMemory] = None

    def _get_mem(self) -> LongTermMemory:
        if self._mem is None:
            self._mem = get_long_term_memory()
        return self._mem

    def can_write(self, agent_name: str) -> bool:
        """检查 Agent 是否有长期记忆的写入权限。"""
        return agent_name in _WRITE_ENABLED_AGENTS

    def can_read(self, agent_name: str) -> bool:
        """所有 Agent 都可以读取长期记忆。"""
        return True

    # 偏好写入方法（只应由 PreferenceAgent 调用）
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