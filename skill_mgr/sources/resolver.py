"""Source resolution."""

from __future__ import annotations
from pathlib import Path
from skill_mgr.errors import SkillMgrError
from skill_mgr.models import MaterializedSource, SourceDescriptor
from skill_mgr.sources.github import materialize_github_source, parse_github_shorthand


def _local_source(ref: str) -> MaterializedSource | None:
    candidate = Path(ref).expanduser()
    if not candidate.exists():
        return None
    resolved = candidate.resolve()
    if not resolved.is_dir():
        raise SkillMgrError(
            f"Local source '{ref}' is not a directory.",
            code="invalid_local_source",
        )
    return MaterializedSource(
        source=SourceDescriptor(kind="local", ref=ref, path=str(resolved)),
        directory=resolved,
    )


def materialize_source(ref: str) -> MaterializedSource:
    """Resolve a local path or GitHub shorthand into a local directory."""
    local = _local_source(ref)
    if local is not None:
        return local

    github = parse_github_shorthand(ref)
    if github is not None:
        return materialize_github_source(github)

    raise SkillMgrError(
        f"Source '{ref}' does not exist locally and is not valid GitHub shorthand.",
        code="invalid_source",
    )
