from __future__ import annotations
import io
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from skill_mgr.errors import SkillMgrError
from skill_mgr.models import (
    AgentAdapter,
    MaterializedSource,
    SourceDescriptor,
    ValidationError,
)
from skill_mgr.services import SkillManagerService
from tests.helpers import github_archive_bytes, write_skill


@pytest.mark.parametrize("os_name", ["windows", "linux", "macos"])
def test_install_update_uninstall_local_flow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, os_name: str
) -> None:
    home = tmp_path / "home"
    for marker in (".claude", ".codex", ".openclaw", ".orcheo"):
        (home / marker).mkdir(parents=True)
    monkeypatch.setattr("skill_mgr.adapters.registry.current_os_name", lambda: os_name)
    monkeypatch.setattr("pathlib.Path.home", lambda: home)
    service = SkillManagerService()
    source = write_skill(tmp_path / "source" / "demo-skill")

    install_payload = service.install(str(source))
    assert [target["status"] for target in install_payload["targets"]] == [
        "installed",
        "installed",
        "installed",
        "installed",
    ]

    update_payload = service.update(str(source))
    assert [target["status"] for target in update_payload["targets"]] == [
        "updated",
        "updated",
        "updated",
        "updated",
    ]

    show_payload = service.show("demo-skill")
    assert [target["status"] for target in show_payload["targets"]] == [
        "installed",
        "installed",
        "installed",
        "installed",
    ]

    list_payload = service.list()
    assert all(len(target["skills"]) == 1 for target in list_payload["targets"])

    uninstall_payload = service.uninstall("demo-skill")
    assert [target["status"] for target in uninstall_payload["targets"]] == [
        "uninstalled",
        "uninstalled",
        "uninstalled",
        "uninstalled",
    ]


@pytest.mark.parametrize("os_name", ["windows", "linux", "macos"])
def test_install_from_github_repo_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, os_name: str
) -> None:
    home = tmp_path / "home"
    for marker in (".claude", ".codex", ".openclaw", ".orcheo"):
        (home / marker).mkdir(parents=True)
    monkeypatch.setattr("skill_mgr.adapters.registry.current_os_name", lambda: os_name)
    monkeypatch.setattr("pathlib.Path.home", lambda: home)
    service = SkillManagerService()

    archive = github_archive_bytes(
        [
            (
                "owner-repo-main/SKILL.md",
                b"---\nname: demo-skill\ndescription: Demo skill\n---\n\nBody\n",
            ),
            ("owner-repo-main/README.md", b"docs"),
        ]
    )

    def fake_urlopen(request: object, timeout: int = 60) -> io.BytesIO:
        url = request.full_url  # type: ignore[attr-defined]
        if url.endswith("/repos/owner/repo"):
            return io.BytesIO(json.dumps({"default_branch": "main"}).encode("utf-8"))
        return io.BytesIO(archive)

    class ContextResponse(io.BytesIO):
        def __enter__(self) -> ContextResponse:
            return self

        def __exit__(self, *_args: object) -> None:
            self.close()

    def fake_context_urlopen(request: object, timeout: int = 60) -> ContextResponse:
        return ContextResponse(fake_urlopen(request, timeout).read())

    with patch("urllib.request.urlopen", side_effect=fake_context_urlopen):
        payload = service.install("owner/repo")

    assert payload["skill"] == "demo-skill"
    assert all(target["status"] == "installed" for target in payload["targets"])


@pytest.mark.parametrize("os_name", ["windows", "linux", "macos"])
def test_install_from_github_nested_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, os_name: str
) -> None:
    home = tmp_path / "home"
    for marker in (".claude", ".codex", ".openclaw", ".orcheo"):
        (home / marker).mkdir(parents=True)
    monkeypatch.setattr("skill_mgr.adapters.registry.current_os_name", lambda: os_name)
    monkeypatch.setattr("pathlib.Path.home", lambda: home)
    service = SkillManagerService()

    archive = github_archive_bytes(
        [
            (
                "owner-repo-main/skills/demo-skill/SKILL.md",
                b"---\nname: demo-skill\ndescription: Demo skill\n---\n\nBody\n",
            ),
            ("owner-repo-main/skills/demo-skill/README.md", b"docs"),
        ]
    )

    class ContextResponse(io.BytesIO):
        def __enter__(self) -> ContextResponse:
            return self

        def __exit__(self, *_args: object) -> None:
            self.close()

    def fake_urlopen(request: object, timeout: int = 60) -> ContextResponse:
        url = request.full_url  # type: ignore[attr-defined]
        if url.endswith("/repos/owner/repo"):
            return ContextResponse(
                json.dumps({"default_branch": "main"}).encode("utf-8")
            )
        return ContextResponse(archive)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        payload = service.install("owner/repo/skills/demo-skill")

    assert payload["skill"] == "demo-skill"
    assert all(target["status"] == "installed" for target in payload["targets"])


@pytest.mark.parametrize("os_name", ["windows", "linux", "macos"])
def test_validate_reports_invalid_nested_subpath(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    os_name: str,
) -> None:
    home = tmp_path / "home"
    for marker in (".claude", ".codex", ".openclaw", ".orcheo"):
        (home / marker).mkdir(parents=True)
    monkeypatch.setattr("skill_mgr.adapters.registry.current_os_name", lambda: os_name)
    monkeypatch.setattr("pathlib.Path.home", lambda: home)
    service = SkillManagerService()

    archive = github_archive_bytes(
        [
            (
                "owner-repo-main/SKILL.md",
                b"---\nname: demo-skill\ndescription: Demo skill\n---\n\nBody\n",
            )
        ]
    )

    class ContextResponse(io.BytesIO):
        def __enter__(self) -> ContextResponse:
            return self

        def __exit__(self, *_args: object) -> None:
            self.close()

    def fake_urlopen(request: object, timeout: int = 60) -> ContextResponse:
        url = request.full_url  # type: ignore[attr-defined]
        if url.endswith("/repos/owner/repo"):
            return ContextResponse(
                json.dumps({"default_branch": "main"}).encode("utf-8")
            )
        return ContextResponse(archive)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        with pytest.raises(Exception, match="does not exist"):
            service.validate("owner/repo/skills/demo-skill")


@pytest.mark.parametrize("os_name", ["windows", "linux", "macos"])
def test_install_default_skips_undetected_agents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, os_name: str
) -> None:
    home = tmp_path / "home"
    for marker in (".claude", ".codex"):
        (home / marker).mkdir(parents=True)
    monkeypatch.setattr("skill_mgr.adapters.registry.current_os_name", lambda: os_name)
    monkeypatch.setattr("pathlib.Path.home", lambda: home)
    service = SkillManagerService()
    source = write_skill(tmp_path / "source" / "demo-skill")

    payload = service.install(str(source))

    assert [target["status"] for target in payload["targets"]] == [
        "installed",
        "installed",
        "skipped_unavailable",
        "skipped_unavailable",
    ]
    assert payload["targets"][2]["message"] == "agent_not_detected"
    assert payload["targets"][3]["message"] == "agent_not_detected"


@pytest.mark.parametrize("os_name", ["windows", "linux", "macos"])
def test_install_explicit_target_bypasses_detection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, os_name: str
) -> None:
    home = tmp_path / "home"
    monkeypatch.setattr("skill_mgr.adapters.registry.current_os_name", lambda: os_name)
    monkeypatch.setattr("pathlib.Path.home", lambda: home)
    service = SkillManagerService()
    source = write_skill(tmp_path / "source" / "demo-skill")

    payload = service.install(str(source), targets=["openclaw"])

    assert [target["status"] for target in payload["targets"]] == ["installed"]


@pytest.mark.parametrize("os_name", ["windows", "linux", "macos"])
def test_install_reports_already_installed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, os_name: str
) -> None:
    home = tmp_path / "home"
    for marker in (".claude", ".codex", ".openclaw", ".orcheo"):
        (home / marker).mkdir(parents=True)
    monkeypatch.setattr("skill_mgr.adapters.registry.current_os_name", lambda: os_name)
    monkeypatch.setattr("pathlib.Path.home", lambda: home)
    service = SkillManagerService()
    source = write_skill(tmp_path / "source" / "demo-skill")

    service.install(str(source))
    payload = service.install(str(source))

    assert all(target["status"] == "error" for target in payload["targets"])
    assert all(
        target["message"] == "already_installed" for target in payload["targets"]
    )


def test_uninstall_reports_not_installed_when_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    adapter = AgentAdapter(
        name="custom",
        support_by_os={"linux": "supported"},
        install_root_by_os={"linux": str(tmp_path)},
        detection_root_by_os={"linux": str(tmp_path)},
        current_os="linux",
        install_root=tmp_path,
        detection_root=tmp_path,
        available=True,
    )
    monkeypatch.setattr(
        "skill_mgr.services.skill_manager.resolve_targets",
        lambda targets=None: [adapter],
    )
    service = SkillManagerService()
    payload = service.uninstall("demo-skill")
    assert payload["targets"][0]["status"] == "not_installed"


def test_uninstall_skips_unavailable_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    adapter = AgentAdapter(
        name="custom",
        support_by_os={"linux": "supported"},
        install_root_by_os={"linux": str(tmp_path)},
        detection_root_by_os={"linux": str(tmp_path)},
        current_os="linux",
        install_root=tmp_path,
        detection_root=tmp_path,
        available=False,
        availability_reason="unsupported",
    )
    monkeypatch.setattr(
        "skill_mgr.services.skill_manager.resolve_targets",
        lambda targets=None: [adapter],
    )
    service = SkillManagerService()
    payload = service.uninstall("demo-skill")
    assert payload["targets"][0]["status"] == "skipped_unavailable"


def test_list_skips_unavailable_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = AgentAdapter(
        name="custom",
        support_by_os={"linux": "supported"},
        install_root_by_os={"linux": "/tmp"},
        detection_root_by_os={"linux": "/tmp"},
        current_os="linux",
        install_root=Path("/tmp"),
        detection_root=Path("/tmp"),
        available=False,
        availability_reason="unsupported",
    )
    monkeypatch.setattr(
        "skill_mgr.services.skill_manager.resolve_targets",
        lambda targets=None: [adapter],
    )
    service = SkillManagerService()
    payload = service.list()
    assert payload["targets"][0]["status"] == "skipped_unavailable"
    assert payload["targets"][0]["skills"] == []


def test_show_reports_not_installed_when_directory_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    adapter = AgentAdapter(
        name="custom",
        support_by_os={"linux": "supported"},
        install_root_by_os={"linux": str(tmp_path)},
        detection_root_by_os={"linux": str(tmp_path)},
        current_os="linux",
        install_root=tmp_path,
        detection_root=tmp_path,
        available=True,
    )
    monkeypatch.setattr(
        "skill_mgr.services.skill_manager.resolve_targets",
        lambda targets=None: [adapter],
    )
    service = SkillManagerService()
    payload = service.show("demo-skill")
    assert payload["targets"][0]["status"] == "not_installed"
    assert "Skill is not installed" in payload["targets"][0]["message"]


def test_install_invalid_skill_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    mock_source = MaterializedSource(
        source=SourceDescriptor(kind="local", ref=str(tmp_path)),
        directory=tmp_path,
    )
    monkeypatch.setattr(
        "skill_mgr.services.skill_manager.materialize_source",
        lambda ref: mock_source,
    )
    monkeypatch.setattr(
        "skill_mgr.services.skill_manager.validate_skill_directory",
        lambda directory: (
            None,
            [ValidationError(code="missing", field="name", message="oops")],
        ),
    )
    with pytest.raises(SkillMgrError) as exc:
        SkillManagerService().install("none")
    assert exc.value.code == "invalid_skill"


def test_show_skips_unavailable_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = AgentAdapter(
        name="custom",
        support_by_os={"linux": "supported"},
        install_root_by_os={"linux": "/tmp"},
        detection_root_by_os={"linux": "/tmp"},
        current_os="linux",
        install_root=Path("/tmp"),
        detection_root=Path("/tmp"),
        available=False,
        availability_reason="down",
    )
    monkeypatch.setattr(
        "skill_mgr.services.skill_manager.resolve_targets",
        lambda targets=None: [adapter],
    )
    payload = SkillManagerService().show("demo")
    assert payload["targets"][0]["status"] == "skipped_unavailable"


def test_list_handles_non_directory_install_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    install_root = tmp_path / "install_root"
    install_root.write_text("not a dir", encoding="utf-8")
    adapter = AgentAdapter(
        name="custom",
        support_by_os={"linux": "supported"},
        install_root_by_os={"linux": str(install_root)},
        detection_root_by_os={"linux": str(install_root)},
        current_os="linux",
        install_root=install_root,
        detection_root=install_root,
        available=True,
    )
    monkeypatch.setattr(
        "skill_mgr.services.skill_manager.resolve_targets",
        lambda targets=None: [adapter],
    )
    payload = SkillManagerService().list()
    assert payload["targets"][0]["skills"] == []


def test_list_skips_invalid_installed_skill(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    install_root = tmp_path / "install_root"
    candidate = install_root / "demo"
    candidate.mkdir(parents=True)
    adapter = AgentAdapter(
        name="custom",
        support_by_os={"linux": "supported"},
        install_root_by_os={"linux": str(install_root)},
        detection_root_by_os={"linux": str(install_root)},
        current_os="linux",
        install_root=install_root,
        detection_root=install_root,
        available=True,
    )
    monkeypatch.setattr(
        "skill_mgr.services.skill_manager.resolve_targets",
        lambda targets=None: [adapter],
    )
    payload = SkillManagerService().list()
    assert payload["targets"][0]["skills"] == []


def test_read_installed_skill_returns_none_when_invalid(tmp_path: Path) -> None:
    service = SkillManagerService()
    assert service._read_installed_skill(tmp_path) is None
