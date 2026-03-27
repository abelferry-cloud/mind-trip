# app/memory/long_term.py
import aiosqlite
import json
import os
import tempfile
from typing import Any, Dict, List, Optional
from app.config import get_settings

class LongTermMemory:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    user_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, category)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS trip_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    city TEXT NOT NULL,
                    days INTEGER NOT NULL,
                    plan_summary TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    plan_id TEXT NOT NULL,
                    feedback_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    async def update_preference(self, user_id: str, category: str, value: Any):
        val = json.dumps(value) if isinstance(value, list) else json.dumps([value])
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO preferences (user_id, category, value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, category, val))
            await db.commit()

    async def get_preference(self, user_id: str) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT category, value FROM preferences WHERE user_id = ?", (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                result = {}
                for row in rows:
                    result[row["category"]] = json.loads(row["value"])
                return result

    async def save_trip_history(self, user_id: str, city: str, days: int, plan_summary: dict):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO trip_history (user_id, city, days, plan_summary)
                VALUES (?, ?, ?, ?)
            """, (user_id, city, days, json.dumps(plan_summary)))
            await db.commit()

    async def get_trip_history(self, user_id: str) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT city, days, plan_summary, created_at FROM trip_history WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    {"city": r["city"], "days": r["days"],
                     "plan_summary": json.loads(r["plan_summary"]), "created_at": r["created_at"]}
                    for r in rows
                ]

    async def save_feedback(self, user_id: str, plan_id: str, feedback_text: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO feedback (user_id, plan_id, feedback_text) VALUES (?, ?, ?)",
                (user_id, plan_id, feedback_text)
            )
            await db.commit()

    async def close(self):
        pass

_mem_instance: Optional[LongTermMemory] = None
_mem_db_path: Optional[str] = None

def get_long_term_memory(db_path: Optional[str] = None) -> LongTermMemory:
    global _mem_instance, _mem_db_path
    if db_path is None:
        db_path = get_settings().database_url
    if db_path == ":memory:":
        # 对于内存数据库，使用会话期间持久的临时文件
        # 这允许多个连接共享同一个数据库
        if _mem_db_path is None:
            _mem_db_path = os.path.join(tempfile.gettempdir(), "smartjournal_mem.db")
            # 如果存在则删除旧的临时文件
            if os.path.exists(_mem_db_path):
                os.remove(_mem_db_path)
        db_path = _mem_db_path
    if _mem_instance is None or _mem_instance.db_path != db_path:
        _mem_instance = LongTermMemory(db_path)
    return _mem_instance