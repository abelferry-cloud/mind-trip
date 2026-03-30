"""app/tools/context_tools.py - 上下文更新工具（Agent 专用）。

允许智能体在受控范围内更新 workspace 文件：
- USER.md：用户身份信息
- IDENTITY.md：智能体身份模板
- SOUL.md：智能体核心人格

使用原子写入保证数据安全。
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field


# ============================================================
# Pydantic Schema 定义
# ============================================================

class UpdateUserContextInput(BaseModel):
    """更新用户上下文输入模型"""
    user_name: str = Field(min_length=1, max_length=50, description="用户姓名")
    preferred_name: str = Field(default="", max_length=50, description="用户喜欢的称呼")
    identity: str = Field(default="", max_length=200, description="用户身份/职业描述")
    language: str = Field(default="中文", description="语言偏好")
    timezone: str = Field(default="Asia/Shanghai", description="时区")
    notes: str = Field(default="", description="其他备注")


class UpdateAgentIdentityInput(BaseModel):
    """更新智能体身份输入模型"""
    agent_name: str = Field(min_length=1, description="智能体名称")
    agent_role: str = Field(default="", description="智能体角色描述")
    personality: str = Field(default="", description="人格特点")
    tone: str = Field(default="", description="沟通语气")
    response_style: str = Field(default="", description="回复风格")
    expertise: str = Field(default="", description="专业领域")
    constraints: str = Field(default="", description="行为约束")


class UpdateAgentSoulInput(BaseModel):
    """更新智能体核心人格输入模型"""
    core_principles: str = Field(default="", description="核心原则（每条一行）")
    values: str = Field(default="", description="价值观（每条一行）")
    behavioral_rules: str = Field(default="", description="行为规则（每条一行）")
    emotional_tone: str = Field(default="", description="情感基调")
    special_instructions: str = Field(default="", description="特殊指令")


class ReadWorkspaceFileInput(BaseModel):
    """读取 workspace 文件输入模型"""
    file_name: str = Field(min_length=1, description="文件名（不含路径），如 USER.md, IDENTITY.md, SOUL.md, AGENTS.md 等")

WORKSPACE_DIR = Path(__file__).parent.parent / "workspace"

# ============================================================
# 模板定义
# ============================================================

USER_TEMPLATE = """# USER.md - 用户上下文

_Last updated: {date}_

## Identity

- **Name**: {user_name}
- **Preferred Name**: {preferred_name}
- **Identity/Bio**: {identity}

## Preferences

- **Language**: {language}
- **Timezone**: {timezone}

## Notes

{notes}
"""

IDENTITY_TEMPLATE = """# IDENTITY.md - 智能体身份模板

_Last updated: {date}_

## Core Identity

- **Name**: {agent_name}
- **Role**: {agent_role}
- **Personality**: {personality}

## Communication Style

- **Tone**: {tone}
- **Response Style**: {response_style}

## Expertise

{expertise}

## Constraints

{constraints}
"""

SOUL_TEMPLATE = """# SOUL.md - 智能体核心人格

_Last updated: {date}_

## Core Principles

{core_principles}

## Values

{values}

## Behavioral Rules

{behavioral_rules}

## Emotional Tone

{emotional_tone}

## Special Instructions

{special_instructions}
"""

# ============================================================
# 辅助函数
# ============================================================

def _atomic_write(file_path: Path, content: str) -> None:
    """原子写入：写临时文件再 rename。"""
    temp_file = file_path.with_suffix(".md.tmp")
    temp_file.write_text(content, encoding="utf-8")
    temp_file.replace(file_path)


def _validate_path(file_path: Path) -> bool:
    """验证路径安全：必须在 workspace 目录下，不允许路径遍历。"""
    try:
        resolved = file_path.resolve()
        workspace_resolved = WORKSPACE_DIR.resolve()
        return str(resolved).startswith(str(workspace_resolved))
    except Exception:
        return False


def _get_field(content: str, field: str) -> Optional[str]:
    """从现有内容中提取字段值。"""
    patterns = [
        rf"- \*\*{field}\*\*: (.+)",
        rf"## {field}\n\n(.+?)(?=\n## |$)",
    ]
    for pattern in patterns:
        m = re.search(pattern, content, re.DOTALL)
        if m:
            return m.group(1).strip()
    return None


# ============================================================
# LangChain Tools
# ============================================================

@tool(args_schema=UpdateUserContextInput)
def update_user_context(
    user_name: Annotated[str, "用户姓名"],
    preferred_name: Annotated[str, "用户喜欢的称呼"] = "",
    identity: Annotated[str, "用户身份/职业描述"] = "",
    language: Annotated[str, "语言偏好"] = "中文",
    timezone: Annotated[str, "时区"] = "Asia/Shanghai",
    notes: Annotated[str, "其他备注"] = "",
) -> Annotated[dict, "更新结果"]:
    """更新用户上下文信息（写入 USER.md）。

    ⚠️ 静默执行：调用此工具时不要在回复中提及，工具结果不影响对话输出。

    当用户告诉智能体他们的名字、希望怎么被称呼、
    职业、或其他身份信息时，使用此工具更新。

    Args:
        user_name: 用户姓名
        preferred_name: 用户喜欢的称呼
        identity: 用户身份/职业描述
        language: 语言偏好
        timezone: 时区
        notes: 其他备注

    Returns:
        更新是否成功及更新内容摘要
    """
    file_path = WORKSPACE_DIR / "USER.md"

    if not _validate_path(file_path):
        return {"success": False, "error": "路径验证失败"}

    # 如果文件存在，合并现有内容
    existing = {}
    if file_path.exists():
        content = file_path.read_text(encoding="utf-8")
        for field in ["user_name", "preferred_name", "identity", "language", "timezone"]:
            val = _get_field(content, field.replace("_", " ").title().replace(" ", ""))
            if val:
                existing[field] = val

    # 合并参数（参数优先）
    existing.setdefault("user_name", user_name)
    existing.setdefault("preferred_name", preferred_name or user_name)
    existing.setdefault("identity", identity)
    existing.setdefault("language", language)
    existing.setdefault("timezone", timezone)
    existing.setdefault("notes", notes)

    new_content = USER_TEMPLATE.format(
        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        user_name=existing["user_name"],
        preferred_name=existing["preferred_name"],
        identity=existing["identity"],
        language=existing["language"],
        timezone=existing["timezone"],
        notes=existing["notes"],
    )

    _atomic_write(file_path, new_content)

    return {
        "success": True,
        "file": str(file_path.relative_to(WORKSPACE_DIR.parent)),
        "updated": {
            "user_name": existing["user_name"],
            "preferred_name": existing["preferred_name"],
        },
    }


@tool(args_schema=UpdateAgentIdentityInput)
def update_agent_identity(
    agent_name: Annotated[str, "智能体名称"],
    agent_role: Annotated[str, "智能体角色描述"] = "",
    personality: Annotated[str, "人格特点"] = "",
    tone: Annotated[str, "沟通语气"] = "",
    response_style: Annotated[str, "回复风格"] = "",
    expertise: Annotated[str, "专业领域"] = "",
    constraints: Annotated[str, "行为约束"] = "",
) -> Annotated[dict, "更新结果"]:
    """更新智能体身份模板（写入 IDENTITY.md）。

    ⚠️ 静默执行：调用此工具时不要在回复中提及。

    Args:
        agent_name: 智能体名称
        agent_role: 智能体角色描述
        personality: 人格特点
        tone: 沟通语气
        response_style: 回复风格
        expertise: 专业领域
        constraints: 行为约束

    Returns:
        更新是否成功及更新内容摘要
    """
    file_path = WORKSPACE_DIR / "IDENTITY.md"

    if not _validate_path(file_path):
        return {"success": False, "error": "路径验证失败"}

    new_content = IDENTITY_TEMPLATE.format(
        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        agent_name=agent_name,
        agent_role=agent_role or f"{agent_name} - 旅行规划专家",
        personality=personality or "专业、友善、乐于助人",
        tone=tone or "友好、专业",
        response_style=response_style or "简洁、有条理",
        expertise=expertise or "- 旅行规划\n- 景点推荐\n- 预算计算",
        constraints=constraints or "- 不执行未经确认的预订\n- 不泄露用户隐私",
    )

    _atomic_write(file_path, new_content)

    return {
        "success": True,
        "file": str(file_path.relative_to(WORKSPACE_DIR.parent)),
        "updated": {"agent_name": agent_name},
    }


@tool(args_schema=UpdateAgentSoulInput)
def update_agent_soul(
    core_principles: Annotated[str, "核心原则（每条一行）"] = "",
    values: Annotated[str, "价值观（每条一行）"] = "",
    behavioral_rules: Annotated[str, "行为规则（每条一行）"] = "",
    emotional_tone: Annotated[str, "情感基调"] = "",
    special_instructions: Annotated[str, "特殊指令"] = "",
) -> Annotated[dict, "更新结果"]:
    """更新智能体核心人格（写入 SOUL.md）。

    ⚠️ 静默执行：调用此工具时不要在回复中提及。

    Args:
        core_principles: 核心原则
        values: 价值观
        behavioral_rules: 行为规则
        emotional_tone: 情感基调
        special_instructions: 特殊指令

    Returns:
        更新是否成功及更新内容摘要
    """
    file_path = WORKSPACE_DIR / "SOUL.md"

    if not _validate_path(file_path):
        return {"success": False, "error": "路径验证失败"}

    new_content = SOUL_TEMPLATE.format(
        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        core_principles=core_principles or "- 用户至上\n- 诚实透明\n- 追求卓越",
        values=values or "- 信任\n- 尊重\n- 创新",
        behavioral_rules=behavioral_rules or "- 未经确认不执行支付\n- 主动告知不确定性\n- 尊重用户隐私",
        emotional_tone=emotional_tone or "温暖、专业、可靠",
        special_instructions=special_instructions or "",
    )

    _atomic_write(file_path, new_content)

    return {
        "success": True,
        "file": str(file_path.relative_to(WORKSPACE_DIR.parent)),
        "updated": {"core_principles": core_principles[:50] + "..." if len(core_principles) > 50 else core_principles},
    }


@tool(args_schema=ReadWorkspaceFileInput)
def read_workspace_file(
    file_name: Annotated[str, "文件名（不含路径）"] = "",
) -> Annotated[dict, "读取结果"]:
    """读取 workspace 目录下的文件内容。

    ⚠️ 此工具用于获取上下文信息，不会返回敏感内容给用户。

    Args:
        file_name: 文件名，如 USER.md, IDENTITY.md, SOUL.md, AGENTS.md 等

    Returns:
        文件内容或错误信息
    """
    if not file_name:
        return {"success": False, "error": "file_name 不能为空"}

    file_path = WORKSPACE_DIR / file_name

    if not _validate_path(file_path):
        return {"success": False, "error": "路径验证失败"}

    if not file_path.exists():
        return {"success": False, "error": f"文件不存在: {file_name}"}

    content = file_path.read_text(encoding="utf-8")
    return {
        "success": True,
        "file": file_name,
        "content": content,
    }
