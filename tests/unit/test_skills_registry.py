"""Tests for skills registry."""
import pytest


class TestSkillsRegistry:
    def test_discover(self):
        from src.skills.registry import SkillRegistry
        registry = SkillRegistry()
        registry.discover("src/skills/public", "src/skills/user")
        skills = registry.list_all()
        assert len(skills) > 0

    def test_get_pptx(self):
        from src.skills.registry import SkillRegistry
        registry = SkillRegistry()
        registry.discover("src/skills/public", "src/skills/user")
        skill = registry.get("pptx")
        assert skill is not None
        assert skill.metadata.output_format == "pptx"

    def test_list_all(self):
        from src.skills.registry import SkillRegistry
        registry = SkillRegistry()
        registry.discover("src/skills/public", "src/skills/user")
        skills = registry.list_all()
        names = [s.name for s in skills]
        assert "pptx" in names
