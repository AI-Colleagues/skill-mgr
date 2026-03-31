"""Core skill-manager services."""

from __future__ import annotations
import shutil
from pathlib import Path
from typing import Any
from skill_mgr.adapters import resolve_targets
from skill_mgr.errors import SkillMgrError
from skill_mgr.fs import atomic_copytree, remove_tree
from skill_mgr.models import AgentAdapter, SkillMetadata
from skill_mgr.sources import materialize_source
from skill_mgr.validation import validate_skill_directory


def _target_result(
    adapter: AgentAdapter,
    *,
    path: Path | None,
    status: str,
    message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "target": adapter.name,
        "path": None if path is None else str(path),
        "status": status,
        "message": message,
        "metadata": metadata,
    }


class SkillManagerService:
    """Install and inspect skills across multiple agent adapters."""

    def __init__(self) -> None:
        """Initialize the service."""

    def validate(self, ref: str) -> dict[str, Any]:
        """Validate a source without installing it."""
        materialized = materialize_source(ref)
        try:
            skill, errors = validate_skill_directory(materialized.directory)
            return {
                "action": "validate",
                "ref": ref,
                "source": materialized.source.to_dict(),
                "valid": skill is not None and not errors,
                "skill": None if skill is None else skill.to_dict(),
                "errors": [error.to_dict() for error in errors],
            }
        finally:
            self._cleanup(materialized)

    def install(self, ref: str, *, targets: list[str] | None = None) -> dict[str, Any]:
        """Install a skill across one or more targets."""
        return self._install_like("install", ref=ref, targets=targets)

    def update(self, ref: str, *, targets: list[str] | None = None) -> dict[str, Any]:
        """Update a skill across one or more targets."""
        return self._install_like("update", ref=ref, targets=targets)

    def uninstall(
        self, name: str, *, targets: list[str] | None = None
    ) -> dict[str, Any]:
        """Uninstall a skill across one or more targets."""
        resolved_targets = resolve_targets(targets)
        results: list[dict[str, Any]] = []
        for adapter in resolved_targets:
            path = None if adapter.install_root is None else adapter.install_root / name
            if not adapter.available:
                results.append(
                    _target_result(
                        adapter,
                        path=path,
                        status="skipped_unavailable",
                        message=adapter.availability_reason,
                    )
                )
                continue
            assert path is not None
            assert adapter.install_root is not None
            if path.exists():
                remove_tree(path, root=adapter.install_root)
                results.append(_target_result(adapter, path=path, status="uninstalled"))
                continue
            results.append(_target_result(adapter, path=path, status="not_installed"))
        return {"skill": name, "action": "uninstall", "targets": results}

    def list(self, *, targets: list[str] | None = None) -> dict[str, Any]:
        """List installed skills across one or more targets."""
        resolved_targets = resolve_targets(targets)
        results: list[dict[str, Any]] = []
        for adapter in resolved_targets:
            if not adapter.available:
                results.append(
                    {
                        "target": adapter.name,
                        "status": "skipped_unavailable",
                        "message": adapter.availability_reason,
                        "skills": [],
                    }
                )
                continue
            assert adapter.install_root is not None
            skills = self._list_target_skills(adapter.install_root)
            results.append(
                {
                    "target": adapter.name,
                    "status": "available",
                    "message": None,
                    "skills": skills,
                }
            )
        return {"action": "list", "targets": results}

    def show(
        self, name: str, *, targets: list[str] | None = None
    ) -> dict[str, Any]:
        """Show one skill across one or more targets."""
        resolved_targets = resolve_targets(targets)
        results: list[dict[str, Any]] = []
        for adapter in resolved_targets:
            path = None if adapter.install_root is None else adapter.install_root / name
            if not adapter.available:
                results.append(
                    _target_result(
                        adapter,
                        path=path,
                        status="skipped_unavailable",
                        message=adapter.availability_reason,
                    )
                )
                continue
            assert path is not None
            if not path.is_dir():
                results.append(
                    _target_result(
                        adapter,
                        path=path,
                        status="not_installed",
                        message="Skill is not installed for this target.",
                    )
                )
                continue
            metadata = self._read_installed_skill(path)
            results.append(
                _target_result(
                    adapter,
                    path=path,
                    status="installed",
                    metadata=None if metadata is None else metadata.to_dict(),
                )
            )
        return {"action": "show", "name": name, "targets": results}

    def _install_like(
        self,
        action: str,
        *,
        ref: str,
        targets: list[str] | None,
    ) -> dict[str, Any]:
        materialized = materialize_source(ref)
        try:
            skill, errors = validate_skill_directory(materialized.directory)
            if skill is None:
                raise SkillMgrError(
                    "; ".join(error.message for error in errors),
                    code="invalid_skill",
                )

            resolved_targets = resolve_targets(targets)
            results: list[dict[str, Any]] = []
            for adapter in resolved_targets:
                path = (
                    None
                    if adapter.install_root is None
                    else adapter.install_root / skill.name
                )
                if not adapter.available:
                    results.append(
                        _target_result(
                            adapter,
                            path=path,
                            status="skipped_unavailable",
                            message=adapter.availability_reason,
                        )
                    )
                    continue
                assert path is not None
                if action == "install" and path.exists():
                    results.append(
                        _target_result(
                            adapter,
                            path=path,
                            status="error",
                            message="already_installed",
                        )
                    )
                    continue
                next_status = (
                    "updated" if path.exists() and action == "update" else "installed"
                )
                atomic_copytree(materialized.directory, path)
                results.append(_target_result(adapter, path=path, status=next_status))
            return {
                "skill": skill.name,
                "action": action,
                "source": materialized.source.to_dict(),
                "targets": results,
            }
        finally:
            self._cleanup(materialized)

    def _list_target_skills(self, root: Path) -> list[dict[str, Any]]:
        if not root.is_dir():
            return []
        rows: list[dict[str, Any]] = []
        for candidate in sorted(path for path in root.iterdir() if path.is_dir()):
            metadata = self._read_installed_skill(candidate)
            if metadata is None:
                continue
            rows.append(
                {
                    "name": metadata.name,
                    "description": metadata.description,
                    "path": str(candidate),
                    "status": "installed",
                }
            )
        return rows

    def _read_installed_skill(self, directory: Path) -> SkillMetadata | None:
        metadata, errors = validate_skill_directory(directory)
        if metadata is None or errors:
            return None
        return metadata

    def _cleanup(self, materialized: Any) -> None:
        cleanup_root = getattr(materialized, "cleanup_root", None)
        if cleanup_root is not None:
            shutil.rmtree(cleanup_root, ignore_errors=True)
