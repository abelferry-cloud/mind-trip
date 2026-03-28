# app/memory/markdown_memory.py
"""MarkdownMemoryManager - Manages MEMORY.md as the curated long-term memory file.

Reference: OpenClaw's "Markdown is Source of Truth" — files are the single source
of truth, not a database. The model only "remembers" what gets written to disk.
"""
import re
from pathlib import Path
from typing import Any, Dict, Optional

MEMORY_TEMPLATE = """# MEMORY.md - Long-term Memory

_Last updated: {date}_

## User Profile

- **Name**: [user's name]
- **Preferred Name**: [what they like to be called]
- **Timezone**: Asia/Shanghai
- **Spending Style**: [节省/适中/奢侈]
- **Travel Style**: [结构化计划/灵活随性]

## Health Notes

- [any health conditions to be aware of]

## Travel Preferences

- **Preferred transport**: [地铁/公交/出租车/步行]
- **Hardships to avoid**: [硬座/红眼航班/转机/爬山]
- **City preferences**: [previously visited cities]

## Key Decisions

- [important planning decisions from past sessions]

---

_Last updated by AI after session_
"""


class MarkdownMemoryManager:
    """Manages MEMORY.md - the curated long-term memory file.

    Implements atomic writes using rename-to-write pattern:
    1. Write to temp file
    2. Rename temp to target (atomic on POSIX)
    """

    def __init__(self, memory_path: Optional[str] = None):
        if memory_path is None:
            memory_path = Path(__file__).parent.parent / "workspace" / "MEMORY.md"
        else:
            memory_path = Path(memory_path)
        self.memory_path = memory_path

    def _ensure_file_exists(self) -> None:
        """Create MEMORY.md from template if it doesn't exist."""
        if not self.memory_path.exists():
            from datetime import datetime
            content = MEMORY_TEMPLATE.format(date=datetime.now().strftime("%Y-%m-%d"))
            self.memory_path.parent.mkdir(parents=True, exist_ok=True)
            self.memory_path.write_text(content, encoding="utf-8")

    def get_memory(self) -> str:
        """Read and return MEMORY.md content.

        Returns empty string if file doesn't exist.
        """
        if not self.memory_path.exists():
            return ""
        return self.memory_path.read_text(encoding="utf-8")

    async def update_user_profile(self, user_id: str, profile: Dict[str, Any]) -> None:
        """Update the User Profile section in MEMORY.md."""
        self._ensure_file_exists()
        content = self.memory_path.read_text(encoding="utf-8")

        from datetime import datetime
        new_profile = f"""## User Profile

- **Name**: {profile.get('name', "[user's name]")}
- **Preferred Name**: {profile.get('preferred_name', '[what they like to be called]')}
- **Timezone**: {profile.get('timezone', 'Asia/Shanghai')}
- **Spending Style**: {profile.get('spending_style', '[节省/适中/奢侈]')}
- **Travel Style**: {profile.get('travel_style', '[结构化计划/灵活随性]')}

"""
        pattern = r"(## User Profile\n\n- \*\*Name\*\*:.*?\n)(?=\n## |\Z)"
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, new_profile, content, count=1, flags=re.DOTALL)
        else:
            content = content.replace("## Health Notes", new_profile + "## Health Notes", 1)

        content = re.sub(
            r"_Last updated: .*?_",
            f"_Last updated: {datetime.now().strftime('%Y-%m-%d')}_",
            content,
        )
        self._atomic_write(content)

    async def update_preference(self, user_id: str, category: str, value: Any) -> None:
        """Update a specific preference category in MEMORY.md."""
        self._ensure_file_exists()
        content = self.memory_path.read_text(encoding="utf-8")

        category_map = {
            "spending_style": ("Spending Style", lambda v: f"- **Spending Style**: {v}"),
            "health": ("Health Notes", lambda v: f"- {v}" if isinstance(v, str) else f"- {', '.join(v)}"),
            "hardships": ("Hardships to avoid", lambda v: f"- {v}" if isinstance(v, str) else f"- {', '.join(v)}"),
            "city_preferences": ("City preferences", lambda v: f"- {v}" if isinstance(v, str) else f"- {', '.join(v)}"),
            "transport": ("Preferred transport", lambda v: f"- **Preferred transport**: {v}"),
        }

        if category not in category_map:
            return

        section_name, formatter = category_map[category]
        new_line = formatter(value)

        section_pattern = rf"(## {section_name}\n\n)(- .*?\n)*"
        if re.search(section_pattern, content):
            entry_pattern = rf"(- {re.escape(str(value))}|- \*\*{re.escape(category.replace('_', ' '))}\*\*:.*?)\n"
            if not re.search(entry_pattern, content):
                content = re.sub(
                    section_pattern,
                    lambda m: m.group(0) + f"- {value}\n",
                    content,
                    count=1,
                )
        else:
            insert_before = "## Key Decisions"
            if insert_before in content:
                content = content.replace(
                    insert_before,
                    f"## {section_name}\n\n{new_line}\n\n{insert_before}",
                    1,
                )
            else:
                content += f"\n## {section_name}\n\n{new_line}\n"

        from datetime import datetime
        content = re.sub(
            r"_Last updated: .*?_",
            f"_Last updated: {datetime.now().strftime('%Y-%m-%d')}_",
            content,
        )
        self._atomic_write(content)

    async def append_decision(self, session_id: str, decision: str) -> None:
        """Append a key decision under '## Key Decisions' section."""
        self._ensure_file_exists()
        content = self.memory_path.read_text(encoding="utf-8")

        key_decisions_marker = "## Key Decisions"
        if key_decisions_marker in content:
            pattern = r"(## Key Decisions\n\n)(- .*?\n)*"
            repl = rf"\1\2- {decision}\n"
            content = re.sub(pattern, repl, content, count=1)
        else:
            content = content.replace("\n---", f"\n## Key Decisions\n\n- {decision}\n\n---", 1)

        from datetime import datetime
        content = re.sub(
            r"_Last updated: .*?_",
            f"_Last updated: {datetime.now().strftime('%Y-%m-%d')}_",
            content,
        )
        self._atomic_write(content)

    def _atomic_write(self, content: str) -> None:
        """Atomic write: write to temp file, then rename to target."""
        temp_file = self.memory_path.with_suffix(".md.tmp")
        temp_file.write_text(content, encoding="utf-8")
        temp_file.replace(self.memory_path)


# Singleton
_memory_mgr: Optional["MarkdownMemoryManager"] = None


def get_markdown_memory_manager() -> "MarkdownMemoryManager":
    """Get the global MarkdownMemoryManager singleton instance."""
    global _memory_mgr
    if _memory_mgr is None:
        from app.config import get_settings
        settings = get_settings()
        _memory_mgr = MarkdownMemoryManager(memory_path=Path(settings.memory_file))
    return _memory_mgr
