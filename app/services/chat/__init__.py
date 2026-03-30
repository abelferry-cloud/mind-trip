# app/services/chat/__init__.py
"""Chat service - 对话服务。"""

from app.services.chat.chat_service import (
    ChatService,
    get_chat_service,
)

__all__ = [
    "ChatService",
    "get_chat_service",
]
