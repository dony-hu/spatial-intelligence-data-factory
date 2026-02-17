from __future__ import annotations

from typing import Any, Dict, List
from pathlib import Path
import importlib.util


class Skill:
    def __init__(self, name, description, entrypoint):
        self.name = name
        self.description = description
        self.entrypoint = entrypoint

    def execute(self, context):
        return {
            "status": "ok",
            "skill": self.name,
            "context": context
        }


class GovernanceRuntime:
    def __init__(self):
        self._skills = {}

    def register_skill(self, skill):
        self._skills[skill.name] = skill

    def load_skills_from_directory(self, dir_path):
        if not dir_path.exists():
            return
        for skill_file in dir_path.glob("*.md"):
            skill_name = skill_file.stem
            skill = Skill(
                name=skill_name,
                description=f"{skill_name} - 从文件加载",
                entrypoint=str(skill_file)
            )
            self.register_skill(skill)

    def execute_skill(self, name, context):
        if name not in self._skills:
            return {
                "status": "error",
                "message": f"Skill not found: {name}"
            }
        return self._skills[name].execute(context)

    def list_skills(self):
        return list(self._skills.keys())
