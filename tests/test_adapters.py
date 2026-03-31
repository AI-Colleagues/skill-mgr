from __future__ import annotations
from pathlib import Path
import pytest
from skill_mgr.adapters import bundled_adapter_matrix, resolve_targets
from skill_mgr.errors import SkillMgrError
from skill_mgr.models import OSName


@pytest.mark.parametrize("os_name", ["windows", "linux", "macos"])
def test_resolve_targets_all_supported(os_name: OSName, tmp_path: Path) -> None:
    targets = resolve_targets(["all"], current_os=os_name, home=tmp_path)
    assert [target.name for target in targets] == [
        "claude",
        "codex",
        "openclaw",
        "orcheo",
    ]
    assert all(target.available for target in targets)


@pytest.mark.parametrize("os_name", ["windows", "linux", "macos"])
def test_resolve_targets_default_only_uses_detected_agents(
    os_name: OSName, tmp_path: Path
) -> None:
    (tmp_path / ".claude").mkdir(parents=True)
    (tmp_path / ".codex").mkdir(parents=True)
    targets = resolve_targets(None, current_os=os_name, home=tmp_path)

    assert [target.name for target in targets] == [
        "claude",
        "codex",
        "openclaw",
        "orcheo",
    ]
    assert [target.available for target in targets] == [True, True, False, False]
    assert targets[2].availability_reason == "agent_not_detected"
    assert targets[3].availability_reason == "agent_not_detected"


@pytest.mark.parametrize("os_name", ["windows", "linux", "macos"])
def test_resolve_targets_explicit_target_bypasses_detection(
    os_name: OSName, tmp_path: Path
) -> None:
    targets = resolve_targets(["openclaw"], current_os=os_name, home=tmp_path)

    assert [target.name for target in targets] == ["openclaw"]
    assert targets[0].available is True
    assert targets[0].availability_reason is None


def test_resolve_targets_rejects_all_plus_explicit(tmp_path: Path) -> None:
    with pytest.raises(SkillMgrError, match="cannot be combined"):
        resolve_targets(["all", "codex"], current_os="macos", home=tmp_path)


def test_resolve_targets_deduplicates(tmp_path: Path) -> None:
    targets = resolve_targets(["CoDeX", "codex"], current_os="linux", home=tmp_path)
    assert [target.name for target in targets] == ["codex"]


def test_support_matrix_lists_all_bundled_adapters() -> None:
    payload = bundled_adapter_matrix()
    assert payload["action"] == "support-matrix"
    assert [row["adapter"] for row in payload["targets"]] == [
        "claude",
        "codex",
        "openclaw",
        "orcheo",
    ]
