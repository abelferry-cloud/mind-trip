# app/services/memory/__init__.py
"""Memory services - 会话级、长期、日志记忆管理。

从 app/memory/ 重构而来，所有记忆相关逻辑统一放在此包。
"""

from app.services.memory.session_manager import (
    SessionMemoryManager,
    ConversationBufferMemory,
    get_session_memory_manager,
    SessionInfo,
)
from app.services.memory.daily_log import (
    DailyLogManager,
    get_daily_log_manager,
)
from app.services.memory.markdown_memory import (
    MarkdownMemoryManager,
    get_markdown_memory_manager,
)
from app.services.memory.short_term import (
    ShortTermMemory,
    get_short_term_memory,
    HumanMessage,
    AIMessage,
)
from app.services.memory.memory_injector import (
    MemoryInjector,
    get_memory_injector,
)

__all__ = [
    # session
    "SessionMemoryManager",
    "ConversationBufferMemory",
    "get_session_memory_manager",
    "SessionInfo",
    # daily log
    "DailyLogManager",
    "get_daily_log_manager",
    # markdown memory
    "MarkdownMemoryManager",
    "get_markdown_memory_manager",
    # short term
    "ShortTermMemory",
    "get_short_term_memory",
    "HumanMessage",
    "AIMessage",
    # injector
    "MemoryInjector",
    "get_memory_injector",
]
