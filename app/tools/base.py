# app/tools/base.py
"""工具基础设施：异常类与标准返回格式"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ToolErrorCategory(Enum):
    """工具错误分类"""
    API_ERROR = "API_ERROR"           # 外部 API 错误
    VALIDATION_ERROR = "VALIDATION_ERROR"  # 参数验证错误
    NETWORK_ERROR = "NETWORK_ERROR"   # 网络连接错误
    TIMEOUT_ERROR = "TIMEOUT_ERROR"   # 请求超时
    UNKNOWN_ERROR = "UNKNOWN_ERROR"  # 未知错误


class ToolException(Exception):
    """工具异常类"""

    def __init__(
        self,
        category: ToolErrorCategory,
        message: str,
        details: Optional[dict] = None,
        retryable: bool = False
    ):
        self.category = category
        self.message = message
        self.details = details or {}
        self.retryable = retryable
        super().__init__(message)

    def __repr__(self):
        return f"ToolException({self.category.value}, {self.message!r})"


@dataclass
class ToolResult:
    """工具执行结果标准格式"""
    success: bool
    data: Any = None
    error: ToolException = None
    metadata: dict = field(default_factory=dict)

    @property
    def tool_name(self) -> str:
        return self.metadata.get("tool_name", "unknown")

    @property
    def duration_ms(self) -> int:
        return self.metadata.get("duration_ms", 0)

    @property
    def cached(self) -> bool:
        return self.metadata.get("cached", False)

    @property
    def retry_count(self) -> int:
        return self.metadata.get("retry_count", 0)
