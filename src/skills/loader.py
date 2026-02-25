"""Dynamic skill loader -- discovers and imports skill modules at runtime."""

import importlib
import importlib.util
import inspect
import sys
from pathlib import Path

from src.skills.base import BaseSkill
from src.utils.logging import get_logger

logger = get_logger(__name__)


def _module_name_for(path: Path) -> str:
    """Derive a unique, deterministic module name from a file path."""
    return f"_skills_dynamic_.{path.stem}_{hash(str(path)) & 0xFFFFFFFF:08x}"


def load_skills_from_directory(directory: str | Path) -> list[BaseSkill]:
    """Scan *directory* for ``*_skill.py`` files, import them, and return
    instantiated :class:`BaseSkill` subclasses found inside.

    Parameters
    ----------
    directory:
        Filesystem path to scan.  Non-existent or empty directories are
        handled gracefully (an empty list is returned).

    Returns
    -------
    list[BaseSkill]
        Instances of every concrete ``BaseSkill`` subclass discovered.
    """
    directory = Path(directory)

    if not directory.exists():
        logger.warning("skills_directory_missing", path=str(directory))
        return []

    if not directory.is_dir():
        logger.warning("skills_path_not_directory", path=str(directory))
        return []

    skills: list[BaseSkill] = []

    for filepath in sorted(directory.glob("*_skill.py")):
        try:
            instances = load_skills_from_file(filepath)
            skills.extend(instances)
        except Exception:
            logger.exception("skill_file_load_error", path=str(filepath))

    return skills


def load_skills_from_file(filepath: str | Path) -> list[BaseSkill]:
    """Import a single Python file and return instances of any
    :class:`BaseSkill` subclasses defined in it.

    Parameters
    ----------
    filepath:
        Absolute or relative path to a ``.py`` file.

    Returns
    -------
    list[BaseSkill]
        Instantiated skill objects.
    """
    filepath = Path(filepath)

    if not filepath.exists():
        logger.warning("skill_file_missing", path=str(filepath))
        return []

    module_name = _module_name_for(filepath)

    # Build a module spec from the file path.
    spec = importlib.util.spec_from_file_location(module_name, str(filepath))
    if spec is None or spec.loader is None:
        logger.error("skill_spec_creation_failed", path=str(filepath))
        return []

    module = importlib.util.module_from_spec(spec)

    # Register in sys.modules so intra-module imports work.
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception:
        logger.exception("skill_module_exec_error", path=str(filepath))
        # Clean up on failure.
        sys.modules.pop(module_name, None)
        return []

    return _extract_skill_instances(module, filepath)


def _extract_skill_instances(module: object, filepath: Path) -> list[BaseSkill]:
    """Walk all members of *module* and instantiate concrete BaseSkill subclasses."""
    skills: list[BaseSkill] = []

    for name, obj in inspect.getmembers(module, inspect.isclass):
        if not issubclass(obj, BaseSkill):
            continue
        if obj is BaseSkill:
            continue
        if inspect.isabstract(obj):
            continue

        try:
            instance = obj()
            skills.append(instance)
            logger.info(
                "skill_loaded",
                skill_name=instance.metadata.name,
                file=str(filepath),
            )
        except Exception:
            logger.exception("skill_instantiation_error", cls=name, path=str(filepath))

    return skills
