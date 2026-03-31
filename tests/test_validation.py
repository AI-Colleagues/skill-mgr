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


def test_validate_skill_directory_rejects_invalid_frontmatter(tmp_path: Path) -> None:
    skill_dir = tmp_path / "invalid-frontmatter"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo\n", encoding="utf-8"
    )  # missing closing delimiter
    metadata, errors = validate_skill_directory(skill_dir)
    assert metadata is None
    assert errors[0].code == "invalid_frontmatter"


def test_validate_skill_directory_rejects_invalid_metadata_type(tmp_path: Path) -> None:
    skill_dir = write_skill(
        tmp_path / "demo",
        extra_frontmatter="metadata: []",
    )
    metadata, errors = validate_skill_directory(skill_dir)
    assert metadata is None
    assert errors[0].code == "invalid_metadata"


def test_validate_skill_directory_rejects_invalid_allowed_tools(tmp_path: Path) -> None:
    skill_dir = write_skill(
        tmp_path / "demo",
        extra_frontmatter="allowed-tools:\n  - tool",
    )
    metadata, errors = validate_skill_directory(skill_dir)
    assert metadata is None
    assert errors[0].code == "invalid_allowed_tools"


def test_validate_skill_directory_records_extra_fields(tmp_path: Path) -> None:
    skill_dir = write_skill(
        tmp_path / "demo",
        extra_frontmatter="category: helper",
    )
    metadata, errors = validate_skill_directory(skill_dir)
    assert errors == []
    assert metadata is not None
    assert metadata.extra_fields == {"category": "helper"}


def test_validate_skill_directory_requires_description(tmp_path: Path) -> None:
    skill_dir = tmp_path / "no-desc"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: demo\n---\n", encoding="utf-8")
    metadata, errors = validate_skill_directory(skill_dir)
    assert metadata is None
    assert any(error.code == "missing_description" for error in errors)


def test_validate_skill_directory_rejects_missing_frontmatter_start(
    tmp_path: Path,
) -> None:
    skill_dir = tmp_path / "no-front"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("name: demo\n---\n", encoding="utf-8")
    metadata, errors = validate_skill_directory(skill_dir)
    assert metadata is None
    assert errors[0].code == "invalid_frontmatter"


def test_validate_skill_directory_rejects_bad_frontmatter_line(tmp_path: Path) -> None:
    skill_dir = tmp_path / "bad-line"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "--- invalid\nname: demo\n---\n", encoding="utf-8"
    )
    metadata, errors = validate_skill_directory(skill_dir)
    assert metadata is None
    assert errors[0].code == "invalid_frontmatter"


def test_validate_skill_directory_rejects_yaml_errors(tmp_path: Path) -> None:
    skill_dir = tmp_path / "bad-yaml"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: [invalid\n---\n", encoding="utf-8")
    metadata, errors = validate_skill_directory(skill_dir)
    assert metadata is None
    assert errors[0].code == "invalid_frontmatter"


def test_validate_skill_directory_rejects_non_mapping_frontmatter(
    tmp_path: Path,
) -> None:
    skill_dir = tmp_path / "non-map"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\n- item\n---\n", encoding="utf-8")
    metadata, errors = validate_skill_directory(skill_dir)
    assert metadata is None
    assert errors[0].code == "invalid_frontmatter"


def test_validate_skill_directory_accepts_optional_strings(tmp_path: Path) -> None:
    skill_dir = write_skill(
        tmp_path / "optional",
        extra_frontmatter="license: MIT\ncompatibility: linux\nallowed-tools: helper",
    )
    metadata, errors = validate_skill_directory(skill_dir)
    assert errors == []
    assert metadata is not None
    assert metadata.license == "MIT"
    assert metadata.compatibility == "linux"
    assert metadata.allowed_tools == "helper"
