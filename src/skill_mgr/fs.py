"""Filesystem helpers."""

from __future__ import annotations
import shutil
import tempfile
from pathlib import Path
from skill_mgr.errors import SkillMgrError


def atomic_copytree(source_dir: Path, destination_dir: Path) -> None:
    """Copy a directory via a temporary sibling and swap it into place."""
    destination_dir.parent.mkdir(parents=True, exist_ok=True)
    temp_root = Path(
        tempfile.mkdtemp(prefix=f".{destination_dir.name}-", dir=destination_dir.parent)
    )
    temp_destination = temp_root / destination_dir.name
    try:
        shutil.copytree(source_dir, temp_destination)
        if destination_dir.exists():
            shutil.rmtree(destination_dir)
        temp_destination.replace(destination_dir)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def ensure_within_root(path: Path, root: Path) -> None:
    """Ensure ``path`` resolves inside ``root``."""
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    if resolved_path == resolved_root:
        return
    if resolved_root not in resolved_path.parents:
        raise SkillMgrError(
            f"Refusing to operate on '{path}' outside managed root '{root}'.",
            code="unsafe_path",
        )


def remove_tree(path: Path, *, root: Path) -> None:
    """Delete ``path`` only if it is inside ``root``."""
    ensure_within_root(path, root)
    if path.exists():
        shutil.rmtree(path)
