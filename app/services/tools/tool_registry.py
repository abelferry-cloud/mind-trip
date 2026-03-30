"""app/services/tools/tool_registry.py - 工具注册表。

提供工具的 JSON Schema 声明，供 ModelRouter 在 tool_calling 时使用。
遵循 OpenAI Tool Calling 协议。
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

# 全局工具注册表
_tool_registry: Dict[str, "ToolDef"] = {}


@dataclass
class ToolDef:
    """工具定义。"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema for parameters
    func: Callable[..., Any]  # 实际执行的函数


def get_tool(name: str) -> Optional[ToolDef]:
    return _tool_registry.get(name)


def get_all_tools() -> List[ToolDef]:
    return list(_tool_registry.values())


def get_tools_schema() -> List[Dict[str, Any]]:
    """返回所有工具的 JSON Schema 数组（用于 LLM API）。"""
    tools = []
    for tool in get_all_tools():
        tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
        })
    return tools


def register_tool(
    name: str,
    description: str,
    parameters: Dict[str, Any],
    func: Callable[..., Any],
) -> None:
    """注册一个工具到注册表。"""
    _tool_registry[name] = ToolDef(
        name=name,
        description=description,
        parameters=parameters,
        func=func,
    )


def register_tools_from_module(module: Any, tool_names: List[str]) -> None:
    """从模块批量注册工具。

    Args:
        module: 包含 @tool 装饰器函数的模块
        tool_names: 要注册的工具函数名列表
    """
    for name in tool_names:
        attr = getattr(module, name, None)
        if attr is None:
            continue
        # 从 LangChain tool 获取元数据
        if hasattr(attr, "name") and hasattr(attr, "description"):
            # LangChain @tool 装饰器
            params_schema = getattr(attr, "args_schema", None)
            if params_schema:
                params = _langchain_schema_to_json(params_schema)
            else:
                params = {"type": "object", "properties": {}, "required": []}

            register_tool(
                name=attr.name,
                description=attr.description,
                parameters=params,
                func=attr,
            )


def _langchain_schema_to_json(schema: Any) -> Dict[str, Any]:
    """将 LangChain Pydantic schema 转换为 JSON Schema。"""
    if schema is None:
        return {"type": "object", "properties": {}, "required": []}

    properties = {}
    required = []

    # 检查是否是 Pydantic BaseModel
    if hasattr(schema, "model_fields"):
        # Pydantic v2
        for field_name, field_info in schema.model_fields.items():
            json_type = _python_type_to_json_type(field_info.annotation)
            properties[field_name] = {
                "type": json_type,
                "description": field_info.description or "",
            }
            if field_info.is_required():
                required.append(field_name)
    elif hasattr(schema, "fields"):
        # Pydantic v1
        for field_name, field_info in schema.fields.items():
            json_type = _python_type_to_json_type(field_info.annotation)
            properties[field_name] = {
                "type": json_type,
                "description": field_info.field_info.description or "",
            }
            if field_info.required:
                required.append(field_name)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def _python_type_to_json_type(annotation: Any) -> str:
    """将 Python 类型映射到 JSON Schema 类型。"""
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }
    origin = getattr(annotation, "__origin__", None)
    if origin is not None:
        # 处理 List[T], Dict[K, V] 等泛型
        return type_map.get(origin, "string")
    return type_map.get(annotation, "string")


# ============================================================
# 初始化：注册所有工具
# ============================================================

def _register_all_tools() -> None:
    """在应用启动时注册所有可用工具。"""
    try:
        from app.tools import context_tools

        # 注册上下文更新工具
        register_tools_from_module(context_tools, [
            "update_user_context",
            "update_agent_identity",
            "update_agent_soul",
            "read_workspace_file",
        ])
    except Exception as e:
        import structlog
        logger = structlog.get_logger()
        logger.warning("failed_to_register_tools", error=str(e))


# 单例启动
_register_all_tools()
