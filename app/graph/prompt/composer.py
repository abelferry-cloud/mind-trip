"""app/graph/prompt/composer.py — PromptComposer: 三层 Prompt 组合器。

LangChain Runnable — 协调 Layer 1/2/3 的加载顺序，组合为最终 prompt 字符串。
"""
from datetime import datetime
from typing import Any, Dict, Literal

from langchain_core.runnables import Runnable

from app.graph.prompt.system_builder import SystemPromptBuilder
from app.graph.prompt.workspace_loader import WorkspaceLoader
from app.graph.prompt.memory_loader import MemoryLoader


class PromptComposer(Runnable):
    """三层 Prompt 组合器（LangChain Runnable）。

    使用方式（嵌入 LCEL 链）:
        composer = PromptComposer(agent_name="Supervisor", agent_type="...", mode="main")
        chain = composer | chat_model | output_parser
    """

    def __init__(
        self,
        agent_name: str,
        agent_type: str = "",
        mode: Literal["main", "shared"] = "main",
    ):
        self.agent_name = agent_name
        self.agent_type = agent_type
        self.mode = mode
        self._system_builder = SystemPromptBuilder()
        self._workspace_loader = WorkspaceLoader(mode=mode)
        self._memory_loader = MemoryLoader()

    def invoke(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """组合三层 Prompt。

        Args:
            input: 包含 user_id, session_id, 以及其他动态上下文

        Returns:
            {
                "system_prompt": str,
                "agent_name": str,
                "agent_type": str,
                "mode": str,
                "workspace_loaded_at": ISO datetime,
            }
        """
        user_id = input.get("user_id", "")
        session_id = input.get("session_id", "")
        mode = input.get("session_mode", self.mode)

        # Layer 1: System Prompt
        layer1 = self._system_builder.load(self.agent_name)

        # Layer 2: Workspace
        layer2_result = self._workspace_loader.invoke({"session_mode": mode})
        layer2 = layer2_result["workspace_prompt"]

        # Layer 3: Memory
        layer3 = self._memory_loader.load(user_id, session_id, mode)

        # 组合
        parts = []
        if layer1:
            parts.append(f"## System Prompt\n\n{layer1}")
        if layer2:
            parts.append(f"## Workspace Context\n\n{layer2}")
        if layer3:
            parts.append(f"## Memory\n\n{layer3}")

        system_prompt = "\n\n".join(parts)

        return {
            "system_prompt": system_prompt,
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "mode": mode,
            "workspace_loaded_at": datetime.now().isoformat(),
        }

    def batch(self, inputs: list, **kwargs) -> list:
        return [self.invoke(i, **kwargs) for i in inputs]

    def stream(self, input, **kwargs):
        yield self.invoke(input, **kwargs)