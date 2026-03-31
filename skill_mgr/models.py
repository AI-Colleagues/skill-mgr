"""Shared data models."""

from __future__ import annotations
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal


OSName = Literal["windows", "linux", "macos"]
SupportState = Literal["supported", "unsupported", "unknown"]
ResultStatus = Literal[
    "installed",
    "updated",
    "uninstalled",
    "not_installed",
    "skipped_unavailable",
    "error",
]
SourceKind = Literal["local", "github"]


@dataclass(slots=True)
class SkillMetadata:
    """Validated skill metadata."""

    name: str
    description: str
    license: str | None = None
    compatibility: str | None = None
    metadata: dict[str, Any] | None = None
    allowed_tools: str | None = None
    extra_fields: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly representation."""
        return asdict(self)


@dataclass(slots=True)
class ValidationError:
    """A single skill validation error."""

    code: str
    field: str
    message: str

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-friendly representation."""
        return {"code": self.code, "field": self.field, "message": self.message}


@dataclass(slots=True)
class SourceDescriptor:
    """A normalized source reference."""

    kind: SourceKind
    ref: str
    path: str | None = None
    repository: str | None = None
    subpath: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly representation."""
        data: dict[str, Any] = {"kind": self.kind, "ref": self.ref}
        if self.path is not None:
            data["path"] = self.path
        if self.repository is not None:
            data["repository"] = self.repository
        if self.subpath is not None:
            data["subpath"] = self.subpath
        return data


@dataclass(slots=True)
class MaterializedSource:
    """A resolved local skill directory."""

    source: SourceDescriptor
    directory: Path
    cleanup_root: Path | None = None


@dataclass(slots=True)
class AgentAdapter:
    """Adapter definition and current-machine resolution."""

    name: str
    support_by_os: dict[OSName, SupportState]
    install_root_by_os: dict[OSName, str | None]
    current_os: OSName
    install_root: Path | None = None
    available: bool = False
    availability_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly representation."""
        return {
            "name": self.name,
            "support_by_os": self.support_by_os,
            "install_root_by_os": self.install_root_by_os,
            "current_os": self.current_os,
            "install_root": None
            if self.install_root is None
            else str(self.install_root),
            "available": self.available,
            "availability_reason": self.availability_reason,
        }
