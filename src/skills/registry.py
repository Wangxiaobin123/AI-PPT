"""Central registry that discovers, stores, and looks up skills."""

from __future__ import annotations

from src.skills.base import BaseSkill
from src.skills.loader import load_skills_from_directory
from src.skills.models import SkillMetadata
from src.utils.exceptions import SkillNotFoundError
from src.utils.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Intent-type  ->  output format mapping.
# Used by ``match()`` to translate a high-level intent string (e.g.
# "create_pptx") into the output_format advertised by a registered skill.
# ---------------------------------------------------------------------------
_INTENT_FORMAT_MAP: dict[str, str] = {
    "create_pptx": "pptx",
    "create_docx": "docx",
    "create_xlsx": "xlsx",
    "create_pdf": "pdf",
    "create_html": "html",
    "pptx": "pptx",
    "docx": "docx",
    "xlsx": "xlsx",
    "pdf": "pdf",
    "html": "html",
    "presentation": "pptx",
    "document": "docx",
    "spreadsheet": "xlsx",
    "report": "pdf",
    "webpage": "html",
}


class SkillRegistry:
    """Singleton-style registry for all skills.

    Typical lifecycle::

        registry = SkillRegistry()
        registry.discover(public_dir="./src/skills/public",
                          user_dir="./src/skills/user")
        skill = registry.match("create_pptx", params)
        result = await skill.execute(params, context)
    """

    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(
        self,
        public_dir: str = "./src/skills/public",
        user_dir: str = "./src/skills/user",
    ) -> int:
        """Scan *public_dir* and *user_dir* for ``*_skill.py`` files,
        instantiate skills, and register them.

        Returns the total number of newly registered skills.
        """
        count = 0

        for directory in (public_dir, user_dir):
            instances = load_skills_from_directory(directory)
            for skill in instances:
                self.register(skill)
                count += 1

        logger.info("skills_discovered", count=count)
        return count

    # ------------------------------------------------------------------
    # Registration & lookup
    # ------------------------------------------------------------------

    def register(self, skill: BaseSkill) -> None:
        """Add *skill* to the registry, keyed by its metadata name.

        If a skill with the same name already exists it will be overwritten
        (user skills can therefore override public skills).
        """
        name = skill.metadata.name
        if name in self._skills:
            logger.warning(
                "skill_overwritten",
                skill_name=name,
                old_version=self._skills[name].metadata.version,
                new_version=skill.metadata.version,
            )
        self._skills[name] = skill
        logger.debug("skill_registered", skill_name=name)

    def get(self, name: str) -> BaseSkill:
        """Return the skill registered under *name*.

        Raises :class:`SkillNotFoundError` if no such skill exists.
        """
        skill = self._skills.get(name)
        if skill is None:
            raise SkillNotFoundError(name)
        return skill

    def match(self, intent_type: str, params: dict | None = None) -> BaseSkill:
        """Find the best skill for the given *intent_type*.

        The lookup strategy is:

        1. Translate *intent_type* via ``_INTENT_FORMAT_MAP`` to an output
           format string.
        2. Find a registered skill whose ``output_format`` matches.
        3. If *params* contains a ``"content_format"`` key, prefer the skill
           whose ``input_formats`` includes that value.

        Raises :class:`SkillNotFoundError` when no suitable skill is found.
        """
        params = params or {}

        # Normalise the intent string.
        intent_lower = intent_type.lower().strip()

        # Direct name match first.
        if intent_lower in self._skills:
            return self._skills[intent_lower]

        # Map intent to desired output format.
        target_format = _INTENT_FORMAT_MAP.get(intent_lower)

        if target_format is None:
            # Last-ditch: try stripping "create_" prefix.
            stripped = intent_lower.removeprefix("create_")
            target_format = _INTENT_FORMAT_MAP.get(stripped, stripped)

        # Collect candidates whose output_format matches.
        candidates: list[BaseSkill] = [
            s for s in self._skills.values()
            if s.metadata.output_format == target_format
        ]

        if not candidates:
            raise SkillNotFoundError(intent_type)

        if len(candidates) == 1:
            return candidates[0]

        # Multiple candidates -- prefer the one that accepts the input format.
        content_format = params.get("content_format", "")
        if content_format:
            for skill in candidates:
                if content_format in skill.metadata.input_formats:
                    return skill

        # Fall back to the first candidate (deterministic because dict is
        # insertion-ordered and we sorted during discovery).
        return candidates[0]

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_all(self) -> list[SkillMetadata]:
        """Return metadata for every registered skill."""
        return [s.metadata for s in self._skills.values()]

    def __len__(self) -> int:
        return len(self._skills)

    def __contains__(self, name: str) -> bool:
        return name in self._skills
