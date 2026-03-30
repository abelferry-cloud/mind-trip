# app/tools/registry.py
"""工具注册中心 - 单例模式管理所有工具"""
import threading
from typing import Any, Callable, Optional


class ToolRegistry:
    """工具注册中心（单例模式）"""

    _instance: Optional["ToolRegistry"] = None
    _tools: dict[str, dict] = {}
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # 双重检查锁定
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._tools = {}
        return cls._instance

    def register(
        self,
        tool: Callable,
        name: str = None,
        description: str = None,
        tags: list = None,
        examples: list = None
    ) -> None:
        """注册工具到注册中心"""
        tool_name = name or getattr(tool, "name", None) or getattr(tool, "__name__", str(tool))

        self._tools[tool_name] = {
            "tool": tool,
            "name": tool_name,
            "description": description or "",
            "tags": tags or [],
            "examples": examples or [],
        }

    def get_tool(self, name: str) -> Optional[Callable]:
        """根据名称获取工具"""
        tool_info = self._tools.get(name)
        return tool_info["tool"] if tool_info else None

    def get_tool_info(self, name: str) -> Optional[dict]:
        """获取工具的完整信息"""
        return self._tools.get(name)

    def list_tools(self, tags: list = None) -> list:
        """列出所有工具，或按标签筛选"""
        if tags is None:
            return [
                {
                    "name": info["name"],
                    "description": info["description"],
                    "tags": info["tags"],
                }
                for info in self._tools.values()
            ]

        return [
            {
                "name": info["name"],
                "description": info["description"],
                "tags": info["tags"],
            }
            for info in self._tools.values()
            if any(tag in info["tags"] for tag in tags)
        ]

    def get_tool_schemas(self) -> list:
        """获取所有工具的 schema（供 LLM 使用）"""
        schemas = []
        for info in self._tools.values():
            tool = info["tool"]
            sig_info = self._get_function_signature(tool)

            schema = {
                "name": info["name"],
                "description": info["description"],
                "parameters": sig_info,
                "tags": info["tags"],
            }

            if info["examples"]:
                schema["examples"] = info["examples"]

            schemas.append(schema)

        return schemas

    def _get_function_signature(self, func: Callable) -> dict:
        """获取函数的参数签名"""
        import inspect

        try:
            sig = inspect.signature(func)
            params = {}

            for param_name, param in sig.parameters.items():
                param_info = {
                    "type": "string",  # 默认类型
                }

                if param.default is not inspect.Parameter.empty:
                    param_info["default"] = param.default

                params[param_name] = param_info

            return {
                "type": "object",
                "properties": params,
            }
        except (ValueError, TypeError):
            return {"type": "object", "properties": {}}


# 全局单例实例
tool_registry = ToolRegistry()
