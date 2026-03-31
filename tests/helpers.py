from __future__ import annotations
import tarfile
from pathlib import Path


def write_skill(
    directory: Path,
    *,
    name: str = "demo-skill",
    description: str = "Demo skill",
    extra_frontmatter: str = "",
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    frontmatter = [
        "---",
        f"name: {name}",
        f"description: {description}",
    ]
    if extra_frontmatter:
        frontmatter.extend(extra_frontmatter.strip().splitlines())
    frontmatter.append("---")
    frontmatter.append("")
    frontmatter.append("Use this skill.")
    (directory / "SKILL.md").write_text("\n".join(frontmatter), encoding="utf-8")
    (directory / "notes.txt").write_text("notes", encoding="utf-8")
    return directory


def make_tarball(archive_path: Path, files: list[tuple[str, bytes]]) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, mode="w:gz") as archive:
        for relative_path, content in files:
            temp_file = archive_path.parent / relative_path
            temp_file.parent.mkdir(parents=True, exist_ok=True)
            temp_file.write_bytes(content)
            archive.add(temp_file, arcname=relative_path)
