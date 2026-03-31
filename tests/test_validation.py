from __future__ import annotations
from pathlib import Path
from skill_mgr.validation import validate_skill_directory
from tests.helpers import write_skill


def test_validate_skill_directory_accepts_valid_skill(tmp_path: Path) -> None:
    skill_dir = write_skill(tmp_path / "demo-skill")
    metadata, errors = validate_skill_directory(skill_dir)
    assert errors == []
    assert metadata is not None
    assert metadata.name == "demo-skill"


def test_validate_skill_directory_requires_skill_md(tmp_path: Path) -> None:
    metadata, errors = validate_skill_directory(tmp_path)
    assert metadata is None
    assert errors[0].code == "missing_skill_md"


def test_validate_skill_directory_rejects_bad_name(tmp_path: Path) -> None:
    skill_dir = write_skill(tmp_path / "bad", name="BadName")
    metadata, errors = validate_skill_directory(skill_dir)
    assert metadata is None
    assert errors[0].code == "invalid_name"


def test_validate_skill_directory_allows_mapping_metadata(tmp_path: Path) -> None:
    skill_dir = write_skill(
        tmp_path / "demo-skill",
        extra_frontmatter='metadata:\n  openclaw:\n    os: ["darwin"]',
    )
    metadata, errors = validate_skill_directory(skill_dir)
    assert errors == []
    assert metadata is not None
    assert metadata.metadata == {"openclaw": {"os": ["darwin"]}}
