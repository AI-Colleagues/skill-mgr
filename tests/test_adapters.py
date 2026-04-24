from __future__ import annotations
import platform
from pathlib import Path
import pytest
from skill_mgr.adapters import bundled_adapter_matrix, resolve_targets
from skill_mgr.adapters.registry import current_os_name
from skill_mgr.errors import SkillMgrError
from skill_mgr.models import AgentAdapter, OSName, SupportState


@pytest.mark.parametrize("os_name", ["windows", "linux", "macos"])
def test_resolve_targets_all_supported(os_name: OSName, tmp_path: Path) -> None:
    targets = resolve_targets(["all"], current_os=os_name, home=tmp_path)
    assert [target.name for target in targets] == [
        "claude",
        "codex",
        "gemini",
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
    (tmp_path / ".gemini").mkdir(parents=True)
    targets = resolve_targets(None, current_os=os_name, home=tmp_path)

    assert [target.name for target in targets] == [
        "claude",
        "codex",
        "gemini",
        "openclaw",
        "orcheo",
    ]
    assert [target.available for target in targets] == [
        True,
        True,
        True,
        False,
        False,
    ]
    assert targets[2].availability_reason is None
    assert targets[3].availability_reason == "agent_not_detected"
    assert targets[4].availability_reason == "agent_not_detected"


@pytest.mark.parametrize("os_name", ["windows", "linux", "macos"])
def test_resolve_targets_explicit_target_bypasses_detection(
    os_name: OSName, tmp_path: Path
) -> None:
    targets = resolve_targets(["gemini"], current_os=os_name, home=tmp_path)

    assert [target.name for target in targets] == ["gemini"]
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
        "gemini",
        "openclaw",
        "orcheo",
    ]


def _adapter_template(
    *,
    name: str,
    os_name: OSName,
    install_root: Path | None,
    detection_root: Path | None,
    support: SupportState = "supported",
) -> AgentAdapter:
    if install_root is None:
        install_path: dict[OSName, str | None] = {os_name: None}
    else:
        install_path = {os_name: str(install_root)}
    if detection_root is None:
        detect_path: dict[OSName, str | None] = {os_name: None}
    else:
        detect_path = {os_name: str(detection_root)}
    return AgentAdapter(
        name=name,
        support_by_os={os_name: support},
        install_root_by_os=install_path,
        detection_root_by_os=detect_path,
        current_os=os_name,
        install_root=install_root,
        detection_root=detection_root,
    )


def test_current_os_name_raises_for_unsupported_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: "haiku")
    with pytest.raises(SkillMgrError, match="Unsupported host OS"):
        current_os_name()


@pytest.mark.parametrize(
    ("system_value", "expected"),
    [
        ("Darwin", "macos"),
        ("Windows", "windows"),
        ("Linux", "linux"),
    ],
)
def test_current_os_name_normalizes_supported_platforms(
    monkeypatch: pytest.MonkeyPatch, system_value: str, expected: str
) -> None:
    monkeypatch.setattr(platform, "system", lambda: system_value)
    assert current_os_name() == expected


def test_resolve_targets_marks_unsupporting_adapter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    adapter = _adapter_template(
        name="custom",
        os_name="linux",
        install_root=tmp_path,
        detection_root=tmp_path,
        support="unsupported",
    )
    monkeypatch.setattr(
        "skill_mgr.adapters.registry.bundled_adapters",
        lambda **kwargs: {"custom": adapter},
    )
    targets = resolve_targets(["custom"], current_os="linux", home=tmp_path)
    assert not targets[0].available
    assert targets[0].availability_reason == "unsupported_os"


def test_resolve_targets_marks_unknown_install_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    adapter = _adapter_template(
        name="custom",
        os_name="linux",
        install_root=None,
        detection_root=tmp_path,
    )
    monkeypatch.setattr(
        "skill_mgr.adapters.registry.bundled_adapters",
        lambda **kwargs: {"custom": adapter},
    )
    targets = resolve_targets(["custom"], current_os="linux", home=tmp_path)
    assert not targets[0].available
    assert targets[0].availability_reason == "unknown_install_root"


def test_resolve_targets_marks_missing_detection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    adapter = _adapter_template(
        name="custom",
        os_name="linux",
        install_root=tmp_path / "skills",
        detection_root=tmp_path / "missing",
    )
    monkeypatch.setattr(
        "skill_mgr.adapters.registry.bundled_adapters",
        lambda **kwargs: {"custom": adapter},
    )
    targets = resolve_targets(None, current_os="linux", home=tmp_path)
    assert not targets[0].available
    assert targets[0].availability_reason == "agent_not_detected"


def test_resolve_targets_rejects_unknown_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "skill_mgr.adapters.registry.bundled_adapters",
        lambda **kwargs: {
            "custom": _adapter_template(
                name="custom",
                os_name="linux",
                install_root=tmp_path,
                detection_root=tmp_path,
            )
        },
    )
    with pytest.raises(SkillMgrError, match="Unsupported target"):
        resolve_targets(["missing"], current_os="linux", home=tmp_path)
