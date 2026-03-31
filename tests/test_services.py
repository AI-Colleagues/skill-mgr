from __future__ import annotations
import io
import json
import tarfile
from pathlib import Path
from unittest.mock import patch
import pytest
from skill_mgr.services import SkillManagerService
from tests.helpers import write_skill


def _make_archive(files: list[tuple[str, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for relative_path, content in files:
            info = tarfile.TarInfo(relative_path)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


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

    archive = _make_archive(
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

    archive = _make_archive(
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

    archive = _make_archive(
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
