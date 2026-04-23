"""SKILL.md parsing and validation."""

from __future__ import annotations
import re
from pathlib import Path
from typing import Any
import yaml
from skill_mgr.models import SkillMetadata, ValidationError


_NAME_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")


def _extract_frontmatter(content: str) -> tuple[dict[str, Any] | None, str]:
    """Extract YAML frontmatter and the markdown body."""
    if not content.startswith("---"):
        return None, content

    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, content

    end_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break
    if end_index is None:
        return None, content

    frontmatter_text = "\n".join(lines[1:end_index])
    body = "\n".join(lines[end_index + 1 :]).strip()
    try:
        data = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError:
        return None, body
    if not isinstance(data, dict):
        return None, body
    return data, body


def _validate_required_string(
    frontmatter: dict[str, Any],
    *,
    field: str,
    code: str,
    message: str,
) -> tuple[str | None, list[ValidationError]]:
    value = frontmatter.get(field)
    if not isinstance(value, str) or not value.strip():
        return None, [ValidationError(code=code, field=field, message=message)]
    return value.strip(), []


def _validate_optional_string(
    frontmatter: dict[str, Any],
    *,
    field: str,
    code: str,
    message: str,
) -> tuple[str | None, list[ValidationError]]:
    value = frontmatter.get(field)
    if value is None:
        return None, []
    if not isinstance(value, str):
        return None, [ValidationError(code=code, field=field, message=message)]
    return value, []


def validate_skill_directory(
    directory: Path,
) -> tuple[SkillMetadata | None, list[ValidationError]]:
    """Validate a skill directory containing ``SKILL.md``."""
    skill_md = directory / "SKILL.md"
    if not skill_md.exists():
        return None, [
            ValidationError(
                code="missing_skill_md",
                field="SKILL.md",
                message="Resolved directory does not contain SKILL.md.",
            )
        ]

    frontmatter, _body = _extract_frontmatter(skill_md.read_text(encoding="utf-8"))
    if frontmatter is None:
        return None, [
            ValidationError(
                code="invalid_frontmatter",
                field="frontmatter",
                message="SKILL.md must start with valid YAML frontmatter.",
            )
        ]

    errors: list[ValidationError] = []
    normalized_name, name_errors = _validate_required_string(
        frontmatter,
        field="name",
        code="missing_name",
        message="name is required.",
    )
    errors.extend(name_errors)
    if normalized_name is not None and not _NAME_PATTERN.fullmatch(normalized_name):
        errors.append(
            ValidationError(
                code="invalid_name",
                field="name",
                message=(
                    "name must be 1-64 chars of lowercase letters, numbers, "
                    "and internal hyphens."
                ),
            )
        )

    normalized_description, description_errors = _validate_required_string(
        frontmatter,
        field="description",
        code="missing_description",
        message="description is required.",
    )
    errors.extend(description_errors)

    version_value, version_errors = _validate_optional_string(
        frontmatter,
        field="version",
        code="invalid_version",
        message="version must be a string when present.",
    )
    errors.extend(version_errors)

    license_value, license_errors = _validate_optional_string(
        frontmatter,
        field="license",
        code="invalid_license",
        message="license must be a string when present.",
    )
    errors.extend(license_errors)

    compatibility, compatibility_errors = _validate_optional_string(
        frontmatter,
        field="compatibility",
        code="invalid_compatibility",
        message="compatibility must be a string when present.",
    )
    errors.extend(compatibility_errors)

    metadata = frontmatter.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        errors.append(
            ValidationError(
                code="invalid_metadata",
                field="metadata",
                message="metadata must be a mapping when present.",
            )
        )
        metadata = None

    allowed_tools, allowed_tools_errors = _validate_optional_string(
        frontmatter,
        field="allowed-tools",
        code="invalid_allowed_tools",
        message="allowed-tools must be a string when present.",
    )
    errors.extend(allowed_tools_errors)

    if errors:
        return None, errors

    known_fields = {
        "name",
        "description",
        "version",
        "license",
        "compatibility",
        "metadata",
        "allowed-tools",
    }
    extra_fields = {
        key: value
        for key, value in frontmatter.items()
        if isinstance(key, str) and key not in known_fields
    }

    return (
        SkillMetadata(
            name=normalized_name or "",
            description=normalized_description or "",
            version=version_value,
            license=license_value,
            compatibility=compatibility,
            metadata=metadata,
            allowed_tools=allowed_tools,
            extra_fields=extra_fields,
        ),
        [],
    )
