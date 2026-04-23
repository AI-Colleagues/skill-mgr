"""Adapter target resolution."""

from __future__ import annotations
import platform
from pathlib import Path
from skill_mgr.adapters.bundled import bundled_adapters
from skill_mgr.errors import SkillMgrError
from skill_mgr.models import AgentAdapter, OSName


def current_os_name() -> OSName:
    """Return the normalized current OS name."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    if system == "windows":
        return "windows"
    if system == "linux":
        return "linux"
    raise SkillMgrError(f"Unsupported host OS '{system}'.", code="unsupported_host_os")


def resolve_targets(
    targets: list[str] | None,
    *,
    current_os: OSName | None = None,
    home: Path | None = None,
) -> list[AgentAdapter]:
    """Resolve CLI target selections into adapter instances."""
    normalized_os = current_os or current_os_name()
    registry = bundled_adapters(current_os=normalized_os, home=home)

    requested = [target.strip().lower() for target in (targets or []) if target.strip()]
    if not requested:
        requested = ["all"]
    implicit_selection = targets is None

    if "all" in requested and len(set(requested)) > 1:
        raise SkillMgrError(
            "`all` cannot be combined with explicit targets.",
            code="invalid_target_selection",
        )

    resolved_names = list(registry) if requested == ["all"] else requested
    seen: set[str] = set()
    resolved: list[AgentAdapter] = []
    for name in resolved_names:
        if name in seen:
            continue
        adapter = registry.get(name)
        if adapter is None:
            supported = ", ".join(sorted(registry))
            raise SkillMgrError(
                f"Unsupported target '{name}'. Use one of: {supported}, all.",
                code="unsupported_target",
            )
        support_state = adapter.support_by_os[normalized_os]
        if support_state == "unsupported":
            adapter.available = False
            adapter.availability_reason = "unsupported_os"
        elif adapter.install_root is None:
            adapter.available = False
            adapter.availability_reason = "unknown_install_root"
        elif (
            implicit_selection
            and adapter.detection_root is not None
            and not adapter.detection_root.exists()
        ):
            adapter.available = False
            adapter.availability_reason = "agent_not_detected"
        else:
            adapter.available = True
        resolved.append(adapter)
        seen.add(name)
    return resolved
