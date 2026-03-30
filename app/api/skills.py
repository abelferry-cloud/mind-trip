"""Skills API - 列出已安装的技能。"""
import json
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/api/skills", tags=["skills"])

SKILLS_DIR = Path(__file__).parent.parent / "skills"


class SkillInfo(BaseModel):
    name: str
    slug: str
    version: str
    published_at: str
    description: str


def _load_skill(dir_name: str, skill_path: Path) -> SkillInfo | None:
    meta_path = skill_path / "_meta.json"
    desc_path = skill_path / "SKILL.md"

    if not meta_path.exists():
        return None

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    description = ""
    if desc_path.exists():
        content = desc_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        # 如果有 YAML frontmatter，从 frontmatter 中提取 description
        if lines and lines[0].strip() == "---":
            try:
                front_end = lines.index("---", 1)
                front_lines = lines[1:front_end]
                for fl in front_lines:
                    if fl.strip().startswith("description:"):
                        description = fl.split("description:", 1)[1].strip().strip('"')
                        break
            except ValueError:
                pass

        # 如果 frontmatter 中没有 description，取第一个非标题、非空行
        if not description:
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#") and line != "---":
                    description = line
                    break
                if line.startswith("# ") and not description:
                    description = line[2:].strip()

    return SkillInfo(
        name=dir_name,
        slug=meta.get("slug", ""),
        version=meta.get("version", ""),
        published_at=str(meta.get("publishedAt", "")),
        description=description,
    )


@router.get("", response_model=List[SkillInfo])
async def list_skills():
    """列出所有已安装的技能。"""
    if not SKILLS_DIR.exists():
        return []

    skills = []
    for entry in sorted(SKILLS_DIR.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        skill = _load_skill(entry.name, entry)
        if skill:
            skills.append(skill)

    return skills
