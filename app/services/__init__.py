# app/services/__init__.py
"""Services 子系统 - 按功能分包的微服务层。

分包结构：
- memory/:     会话、长期、日志记忆管理
- chat/:       对话服务
- model/:      模型路由与调用
- streaming/:  SSE 事件流管理
- tools/:      工具注册与 Tool Calling
"""

# Re-export from sub-packages for backwards compatibility
from app.services.memory import (
    SessionMemoryManager,
    get_session_memory_manager,
    ConversationBufferMemory,
    DailyLogManager,
    get_daily_log_manager,
    MarkdownMemoryManager,
    get_markdown_memory_manager,
    ShortTermMemory,
    get_short_term_memory,
    MemoryInjector,
    get_memory_injector,
    SessionInfo,
    HumanMessage,
    AIMessage,
)
from app.services.chat import ChatService, get_chat_service
from app.services.model import ModelRouter, ModelName, get_model_router
from app.services.streaming import (
    StreamManager,
    get_stream_manager,
    StreamCallbackHandler,
)
from app.services.tools import (
    ToolDef,
    get_tool,
    get_all_tools,
    get_tools_schema,
    register_tool,
    register_tools_from_module,
    ToolCallingService,
    get_tool_calling_service,
)

__all__ = [
    # memory
    "SessionMemoryManager",
    "get_session_memory_manager",
    "ConversationBufferMemory",
    "DailyLogManager",
    "get_daily_log_manager",
    "MarkdownMemoryManager",
    "get_markdown_memory_manager",
    "ShortTermMemory",
    "get_short_term_memory",
    "MemoryInjector",
    "get_memory_injector",
    "SessionInfo",
    "HumanMessage",
    "AIMessage",
    # chat
    "ChatService",
    "get_chat_service",
    # model
    "ModelRouter",
    "ModelName",
    "get_model_router",
    # streaming
    "StreamManager",
    "get_stream_manager",
    "StreamCallbackHandler",
    # tools
    "ToolDef",
    "get_tool",
    "get_all_tools",
    "get_tools_schema",
    "register_tool",
    "register_tools_from_module",
    "ToolCallingService",
    "get_tool_calling_service",
]
