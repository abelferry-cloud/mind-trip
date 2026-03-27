"""System Prompt Builder - 基于 LangChain 的动态 System Prompt 加载器。

参考 OpenClaw 的 workspace 提示词架构：
- Layer 1 (System):  角色定位 / 能力边界 / 安全规则 / 工具指令
- Layer 2 (Workspace): SOUL / USER / MEMORY / AGENTS / TOOLS

设计原则：
1. 每次 chain.invoke() 时重新读取 .md 文件（真正动态）
2. 使用 LangChain Runnable 模式，可嵌入 LCEL 管道
3. MEMORY.md 仅在主会话（main）加载，共享会话（shared）不加载
4. 支持 YAML frontmatter 自动剥离
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional, Dict, Any

from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda


# ============================================================
# Workspace 路径配置
# ============================================================

WORKSPACE_DIR = Path(__file__).parent.parent / "workspace"

# 核心文件（每次加载）
_CORE_FILES = [
    "SOUL.md",
    "IDENTITY.md",
    "USER.md",
    "AGENTS.md",
    "TOOLS.md",
    "BOOTSTRAP.md",
]

# 仅主会话加载的文件
_MAIN_SESSION_ONLY_FILES = ["MEMORY.md"]


# ============================================================
# 底层文件操作
# ============================================================

def _strip_frontmatter(content: str) -> str:
    """去除 Markdown 文件头的 YAML frontmatter (---...--- 块)。"""
    pattern = r'^---\s*\n.*?\n---\s*\n?'
    return re.sub(pattern, "", content, flags=re.DOTALL).strip()


def _read_workspace_file(filename: str) -> Optional[str]:
    """读取 workspace 目录下的 .md 文件，返回剥离 frontmatter 后的内容。

    文件不存在时返回 None，不会抛出异常。
    """
    filepath = WORKSPACE_DIR / filename
    if not filepath.exists():
        return None
    try:
        return _strip_frontmatter(filepath.read_text(encoding="utf-8"))
    except Exception:
        return None


def _section_block(title: str, content: str) -> str:
    """将内容包装为带标题的 Markdown 区块。"""
    return f"\n## {title}\n\n{content}\n"


# ============================================================
# LangChain Runnable: 动态 Workspace Prompt 加载器
# ============================================================

class WorkspacePromptLoader(Runnable):
    """LangChain Runnable — 每次调用时从 workspace 动态加载并组装 System Prompt。

    遵循 OpenClaw 的上下文分层：
    - Layer 2 Workspace: SOUL / IDENTITY / USER / AGENTS / TOOLS / BOOTSTRAP
    - MEMORY.md 仅在 mode="main" 时注入

    使用方式（嵌入 LCEL 链）：
        loader = WorkspacePromptLoader(mode="main", agent_name="Supervisor", agent_type="...")
        chain = loader | chat_model | output_parser

    invoke(input) 接受一个字典，包含可选的 extra_context（额外上下文变量）。
    """

    def __init__(
        self,
        mode: Literal["main", "shared"] = "main",
        agent_name: str = "Agent",
        agent_type: str = "",
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            mode:          "main"（主会话，包含 MEMORY.md）| "shared"（共享上下文，不含 MEMORY.md）
            agent_name:    Agent 名称，作为 prompt 头部标识
            agent_type:    Agent 类型描述
            context:       额外静态上下文（会在 prompt 中以键值对形式注入）
        """
        self.mode = mode
        self.agent_name = agent_name
        self.agent_type = agent_type
        self.context = context or {}

    def _load_workspace_text(self) -> str:
        """从 workspace 目录加载所有相关文件，组装为纯文本 system prompt。"""
        parts = []

        # ---- Layer 2: Workspace 文件（按固定顺序）----
        file_order = _CORE_FILES + (_MAIN_SESSION_ONLY_FILES if self.mode == "main" else [])

        for filename in file_order:
            content = _read_workspace_file(filename)
            if content is None:
                continue
            # 用文件名（去掉 .md）作为区块标题
            section_name = filename.replace(".md", "")
            parts.append(_section_block(section_name, content))

        return "\n".join(parts)

    def _build_system_message(self) -> str:
        """组装完整的 System Prompt 字符串（含头部标识）。"""
        parts = []

        # 头部标识
        header = f"# Agent: {self.agent_name}"
        if self.agent_type:
            header += f"\n# Type: {self.agent_type}"
        header += "\n# Mode: " + self.mode
        parts.append(header)

        # 动态加载 workspace 内容
        workspace_text = self._load_workspace_text()
        if workspace_text:
            parts.append(workspace_text)

        # 静态上下文（额外变量）
        if self.context:
            ctx_lines = [f"- **{k}**: {v}" for k, v in self.context.items()]
            parts.append(_section_block("Context", "\n".join(ctx_lines)))

        return "\n\n".join(parts)

    def invoke(self, input: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """LangChain Runnable.invoke() — 每次调用时动态加载。

        Args:
            input: 包含可选键的字典，支持:
                - session_mode: 覆盖初始化时的 mode
                - dynamic_context: 动态注入的上下文（运行时变量）
                - 其他任意键值对，会拼接到 context 区段

        Returns:
            {"system_prompt": str, "agent_name": str, "mode": str}
        """
        # 允许运行时覆盖 mode
        mode = input.get("session_mode", self.mode)

        # 组装最终 system prompt
        system_prompt = self._build_system_message()

        return {
            "system_prompt": system_prompt,
            "system_prompt_with_context": system_prompt,  # alias，保持兼容
            "agent_name": self.agent_name,
            "mode": mode,
            "workspace_loaded_at": datetime.now().isoformat(),
            # 将输入中的非标准键作为动态上下文透传
            "dynamic_context": {
                k: v for k, v in input.items()
                if k not in ("session_mode",)
            },
        }

    def batch(self, inputs: list, **kwargs) -> list:
        return [self.invoke(i, **kwargs) for i in inputs]

    def stream(self, input, **kwargs):
        yield self.invoke(input, **kwargs)

    def get_config(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "context": self.context,
        }


# ============================================================
# 便捷构造函数（符合 LangChain 惯用模式）
# ============================================================

def build_workspace_prompt_loader(
    mode: Literal["main", "shared"] = "main",
    agent_name: str = "Agent",
    agent_type: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> WorkspacePromptLoader:
    """构建一个 WorkspacePromptLoader（纯函数风格别名）。"""
    return WorkspacePromptLoader(
        mode=mode,
        agent_name=agent_name,
        agent_type=agent_type,
        context=context,
    )


# ============================================================
# 快捷工厂函数：每个 Agent 一个 Loader
# ============================================================

def get_supervisor_loader(
    mode: Literal["main", "shared"] = "main",
    context: Optional[Dict[str, Any]] = None,
) -> WorkspacePromptLoader:
    return build_workspace_prompt_loader(
        mode=mode,
        agent_name="Supervisor",
        agent_type="Planning Coordinator — 协调所有专家 Agent 完成旅行规划",
        context=context,
    )


def get_attractions_loader(
    mode: Literal["main", "shared"] = "main",
    context: Optional[Dict[str, Any]] = None,
) -> WorkspacePromptLoader:
    return build_workspace_prompt_loader(
        mode=mode,
        agent_name="Attractions",
        agent_type="Attractions Specialist — 搜索和推荐旅行景点",
        context=context,
    )


def get_food_loader(
    mode: Literal["main", "shared"] = "main",
    context: Optional[Dict[str, Any]] = None,
) -> WorkspacePromptLoader:
    return build_workspace_prompt_loader(
        mode=mode,
        agent_name="Food",
        agent_type="Food Specialist — 推荐当地美食和餐厅",
        context=context,
    )


def get_hotel_loader(
    mode: Literal["main", "shared"] = "main",
    context: Optional[Dict[str, Any]] = None,
) -> WorkspacePromptLoader:
    return build_workspace_prompt_loader(
        mode=mode,
        agent_name="Hotel",
        agent_type="Hotel Specialist — 搜索和推荐住宿",
        context=context,
    )


def get_budget_loader(
    mode: Literal["main", "shared"] = "main",
    context: Optional[Dict[str, Any]] = None,
) -> WorkspacePromptLoader:
    return build_workspace_prompt_loader(
        mode=mode,
        agent_name="Budget",
        agent_type="Budget Specialist — 计算和验证旅行预算",
        context=context,
    )


def get_route_loader(
    mode: Literal["main", "shared"] = "main",
    context: Optional[Dict[str, Any]] = None,
) -> WorkspacePromptLoader:
    return build_workspace_prompt_loader(
        mode=mode,
        agent_name="Route",
        agent_type="Route Planner — 规划每日行程路线",
        context=context,
    )


def get_preference_loader(
    mode: Literal["main", "shared"] = "main",
    context: Optional[Dict[str, Any]] = None,
) -> WorkspacePromptLoader:
    return build_workspace_prompt_loader(
        mode=mode,
        agent_name="Preference",
        agent_type="Preference Analyst — 解析和更新用户偏好",
        context=context,
    )


# ============================================================
# LangChain ChatPromptTemplate 集成
# ============================================================

def build_supervisor_chat_prompt(
    mode: Literal["main", "shared"] = "main",
    context: Optional[Dict[str, Any]] = None,
) -> ChatPromptTemplate:
    """构建 Supervisor 的 ChatPromptTemplate（内嵌动态 workspace loader）。

    使用方式：
        prompt = build_supervisor_chat_prompt(mode="main")
        chain = prompt | chat_model | output_parser

    内部会在 prompt.invoke() 时先调用 WorkspacePromptLoader，
    将返回的 system_prompt 注入为 SystemMessage。
    """
    loader = get_supervisor_loader(mode=mode, context=context)

    def _load_system_message(input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """在 prompt invoke 时先执行 loader，拿到 system_prompt 后注入 messages。"""
        loader_result = loader.invoke(input_dict)
        system_prompt = loader_result["system_prompt"]
        # 返回的字典会与 input_dict 合并，一起传给 ChatPromptTemplate 格式化
        return {
            **input_dict,
            **loader_result,
            "system_message": ("system", system_prompt),
        }

    # 使用 LCEL 语法：先加载 workspace，再格式化 prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            ("placeholder", "{system_message}"),  # 动态注入
            ("human", "{input}"),
        ]
    )
    return prompt | RunnableLambda(_load_system_message)


# ============================================================
# 底层纯函数（保留兼容）
# ============================================================

def build_session_prompt(mode: Literal["main", "shared"] = "main") -> str:
    """构建纯文本 system prompt（不依赖 LangChain Runnable）。"""
    loader = WorkspacePromptLoader(mode=mode)
    return loader._build_system_message()


def build_core_prompt() -> str:
    """构建核心 system prompt（不包含 MEMORY.md）。"""
    return build_session_prompt(mode="shared")


def build_main_session_prompt() -> str:
    """构建完整 system prompt（包含 MEMORY.md）。"""
    return build_session_prompt(mode="main")
