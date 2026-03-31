from __future__ import annotations
from pathlib import Path
import pytest
from skill_mgr.errors import SkillMgrError
from skill_mgr.fs import atomic_copytree, ensure_within_root, remove_tree


def test_atomic_copytree_replaces_existing_destination(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "skill.txt").write_text("data", encoding="utf-8")
    destination = tmp_path / "destination"
    destination.mkdir()
    (destination / "old.txt").write_text("old", encoding="utf-8")

    atomic_copytree(source, destination)

    assert (destination / "skill.txt").read_text(encoding="utf-8") == "data"
    assert not (destination / "old.txt").exists()


def test_ensure_within_root_accepts_nested_paths(tmp_path: Path) -> None:
    root = tmp_path / "root"
    nested = root / "child"
    nested.mkdir(parents=True)
    ensure_within_root(nested, root)
    ensure_within_root(root, root)


def test_ensure_within_root_rejects_outside_path(tmp_path: Path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "other"
    with pytest.raises(SkillMgrError, match="outside managed root"):
        ensure_within_root(outside, root)


def test_remove_tree_deletes_directory_within_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    target = root / "demo"
    target.mkdir(parents=True)
    (target / "file.txt").write_text("test", encoding="utf-8")

    remove_tree(target, root=root)

    assert not target.exists()


def test_remove_tree_rejects_outside_target(tmp_path: Path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "demo"
    outside.mkdir()
    with pytest.raises(SkillMgrError, match="outside managed root"):
        remove_tree(outside, root=root)


def test_remove_tree_noops_when_target_missing(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    missing = root / "missing"
    remove_tree(missing, root=root)
