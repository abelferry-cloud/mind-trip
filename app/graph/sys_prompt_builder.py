"""app/graph/sys_prompt_builder.py — 向后兼容层。

内部已迁移至 app.graph.prompt 模块。本文件保留以确保
现有调用方（supervisor.py, chat_service.py）无需修改。
"""
from typing import Dict, Any, Literal, Optional

from app.graph.prompt.composer import PromptComposer


def get_supervisor_loader(
    mode: Literal["main", "shared"] = "main",
    context: Optional[Dict[str, Any]] = None,
) -> PromptComposer:
    return PromptComposer(
        agent_name="Supervisor",
        agent_type="Planning Coordinator — 协调所有专家 Agent 完成旅行规划",
        mode=mode,
    )


def get_attractions_loader(
    mode: Literal["main", "shared"] = "main",
    context: Optional[Dict[str, Any]] = None,
) -> PromptComposer:
    return PromptComposer(
        agent_name="Attractions",
        agent_type="Attractions Specialist — 搜索和推荐旅行景点",
        mode=mode,
    )


def get_food_loader(
    mode: Literal["main", "shared"] = "main",
    context: Optional[Dict[str, Any]] = None,
) -> PromptComposer:
    return PromptComposer(
        agent_name="Food",
        agent_type="Food Specialist — 推荐当地美食和餐厅",
        mode=mode,
    )


def get_hotel_loader(
    mode: Literal["main", "shared"] = "main",
    context: Optional[Dict[str, Any]] = None,
) -> PromptComposer:
    return PromptComposer(
        agent_name="Hotel",
        agent_type="Hotel Specialist — 搜索和推荐住宿",
        mode=mode,
    )


def get_budget_loader(
    mode: Literal["main", "shared"] = "main",
    context: Optional[Dict[str, Any]] = None,
) -> PromptComposer:
    return PromptComposer(
        agent_name="Budget",
        agent_type="Budget Specialist — 计算和验证旅行预算",
        mode=mode,
    )


def get_route_loader(
    mode: Literal["main", "shared"] = "main",
    context: Optional[Dict[str, Any]] = None,
) -> PromptComposer:
    return PromptComposer(
        agent_name="Route",
        agent_type="Route Planner — 规划每日行程路线",
        mode=mode,
    )


def get_preference_loader(
    mode: Literal["main", "shared"] = "main",
    context: Optional[Dict[str, Any]] = None,
) -> PromptComposer:
    return PromptComposer(
        agent_name="Preference",
        agent_type="Preference Analyst — 解析和更新用户偏好",
        mode=mode,
    )


# 保留的底层函数
from app.graph.prompt.config import WORKSPACE_DIR
from app.graph.prompt.workspace_loader import WorkspaceLoader
from app.graph.prompt.memory_loader import MemoryLoader


def build_workspace_prompt_loader(
    mode: Literal["main", "shared"] = "main",
    agent_name: str = "Agent",
    agent_type: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> PromptComposer:
    return PromptComposer(
        mode=mode,
        agent_name=agent_name,
        agent_type=agent_type,
    )


def build_session_prompt(mode: Literal["main", "shared"] = "main") -> str:
    from app.graph.prompt.system_builder import SystemPromptBuilder
    from app.graph.prompt.workspace_loader import WorkspaceLoader
    from app.graph.prompt.memory_loader import MemoryLoader

    sb = SystemPromptBuilder()
    wl = WorkspaceLoader(mode=mode)
    ml = MemoryLoader()

    layer1 = sb.load("Agent")
    layer2 = wl.invoke({"session_mode": mode})["workspace_prompt"]
    layer3 = ml.load("", "", mode)

    parts = []
    if layer1:
        parts.append(f"## System Prompt\n\n{layer1}")
    if layer2:
        parts.append(f"## Workspace Context\n\n{layer2}")
    if layer3:
        parts.append(f"## Memory\n\n{layer3}")

    return "\n\n".join(parts)


def build_core_prompt() -> str:
    return build_session_prompt(mode="shared")


def build_main_session_prompt() -> str:
    return build_session_prompt(mode="main")
