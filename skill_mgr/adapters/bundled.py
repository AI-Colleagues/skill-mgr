"""Bundled adapter definitions."""

from __future__ import annotations
from pathlib import Path
from typing import Any, cast
from skill_mgr.models import AgentAdapter, OSName, SupportState


def bundled_adapters(
    *, current_os: OSName, home: Path | None = None
) -> dict[str, AgentAdapter]:
    """Return the bundled adapter registry for the current machine."""
    home_dir = (home or Path.home()).expanduser()

    definitions: dict[str, dict[str, dict[OSName, Any]]] = {
        "claude": {
            "support_by_os": {
                "windows": "supported",
                "linux": "supported",
                "macos": "supported",
            },
            "detection_root_by_os": {
                "windows": "{home}/.claude",
                "linux": "{home}/.claude",
                "macos": "{home}/.claude",
            },
            "install_root_by_os": {
                "windows": "{home}/.claude/skills",
                "linux": "{home}/.claude/skills",
                "macos": "{home}/.claude/skills",
            },
        },
        "codex": {
            "support_by_os": {
                "windows": "supported",
                "linux": "supported",
                "macos": "supported",
            },
            "detection_root_by_os": {
                "windows": "{home}/.codex",
                "linux": "{home}/.codex",
                "macos": "{home}/.codex",
            },
            "install_root_by_os": {
                "windows": "{home}/.codex/skills",
                "linux": "{home}/.codex/skills",
                "macos": "{home}/.codex/skills",
            },
        },
        "openclaw": {
            "support_by_os": {
                "windows": "supported",
                "linux": "supported",
                "macos": "supported",
            },
            "detection_root_by_os": {
                "windows": "{home}/.openclaw",
                "linux": "{home}/.openclaw",
                "macos": "{home}/.openclaw",
            },
            "install_root_by_os": {
                "windows": "{home}/.openclaw/skills",
                "linux": "{home}/.openclaw/skills",
                "macos": "{home}/.openclaw/skills",
            },
        },
        "orcheo": {
            "support_by_os": {
                "windows": "supported",
                "linux": "supported",
                "macos": "supported",
            },
            "detection_root_by_os": {
                "windows": "{home}/.orcheo",
                "linux": "{home}/.orcheo",
                "macos": "{home}/.orcheo",
            },
            "install_root_by_os": {
                "windows": "{home}/.orcheo/skills",
                "linux": "{home}/.orcheo/skills",
                "macos": "{home}/.orcheo/skills",
            },
        },
    }

    return {
            name: AgentAdapter(
                name=name,
                support_by_os=cast(
                    dict[OSName, SupportState], definition["support_by_os"]
                ),
                detection_root_by_os=cast(
                    dict[OSName, str | None], definition["detection_root_by_os"]
                ),
                install_root_by_os=cast(
                    dict[OSName, str | None], definition["install_root_by_os"]
                ),
                current_os=current_os,
                detection_root=Path(
                    definition["detection_root_by_os"][current_os].format(home=home_dir)
                ),
                install_root=Path(
                    definition["install_root_by_os"][current_os].format(home=home_dir)
                ),
            )
        for name, definition in definitions.items()
    }


def bundled_adapter_matrix() -> dict[str, Any]:
    """Return the published bundled-adapter support matrix."""
    return {
        "action": "support-matrix",
        "targets": [
            {
                "adapter": "claude",
                "windows": "supported",
                "linux": "supported",
                "macos": "supported",
                "install_root": "~/.claude/skills",
                "notes": (
                    "Managed skill installs are copied into the agent home directory."
                ),
            },
            {
                "adapter": "codex",
                "windows": "supported",
                "linux": "supported",
                "macos": "supported",
                "install_root": "~/.codex/skills",
                "notes": (
                    "Matches the local Codex skills directory used by the "
                    "desktop app and CLI."
                ),
            },
            {
                "adapter": "openclaw",
                "windows": "supported",
                "linux": "supported",
                "macos": "supported",
                "install_root": "~/.openclaw/skills",
                "notes": (
                    "Matches OpenClaw's documented managed/local skills directory."
                ),
            },
            {
                "adapter": "orcheo",
                "windows": "supported",
                "linux": "supported",
                "macos": "supported",
                "install_root": "~/.orcheo/skills",
                "notes": "Matches Orcheo's managed local skills directory.",
            },
        ],
    }
