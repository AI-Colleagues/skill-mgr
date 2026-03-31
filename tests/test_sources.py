from __future__ import annotations
import io
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from skill_mgr.errors import SkillMgrError
from skill_mgr.sources import materialize_source, parse_github_shorthand
from tests.helpers import github_archive_bytes, write_skill


class MockResponse(io.BytesIO):
    def __enter__(self) -> MockResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def test_parse_github_shorthand_repo_root() -> None:
    source = parse_github_shorthand("owner/repo")
    assert source is not None
    assert source.repository == "owner/repo"
    assert source.subpath is None


def test_parse_github_shorthand_nested_path() -> None:
    source = parse_github_shorthand("owner/repo/skills/demo-skill")
    assert source is not None
    assert source.subpath == "skills/demo-skill"


def test_materialize_source_prefers_existing_local_path(tmp_path: Path) -> None:
    skill_dir = write_skill(tmp_path / "owner" / "repo")
    materialized = materialize_source(str(skill_dir))
    assert materialized.source.kind == "local"
    assert materialized.directory == skill_dir.resolve()


def test_materialize_source_downloads_repo_root(tmp_path: Path) -> None:
    archive = github_archive_bytes(
        [
            (
                "owner-repo-main/SKILL.md",
                b"---\nname: demo-skill\ndescription: Demo skill\n---\n\nBody\n",
            ),
            ("owner-repo-main/notes.txt", b"hello"),
        ]
    )

    def fake_urlopen(request: object, timeout: int = 60) -> MockResponse:
        url = request.full_url  # type: ignore[attr-defined]
        if url.endswith("/repos/owner/repo"):
            return MockResponse(json.dumps({"default_branch": "main"}).encode("utf-8"))
        return MockResponse(archive)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        materialized = materialize_source("owner/repo")

    try:
        assert materialized.source.kind == "github"
        assert (materialized.directory / "SKILL.md").exists()
    finally:
        if materialized.cleanup_root is not None:
            assert materialized.cleanup_root.exists()


def test_materialize_source_uses_json_accept_for_tarball() -> None:
    archive = github_archive_bytes(
        [
            (
                "owner-repo-main/SKILL.md",
                b"---\nname: demo-skill\ndescription: Demo skill\n---\n\nBody\n",
            )
        ]
    )

    def fake_urlopen(request: object, timeout: int = 60) -> MockResponse:
        url = request.full_url  # type: ignore[attr-defined]
        headers = request.headers  # type: ignore[attr-defined]
        if url.endswith("/repos/owner/repo"):
            return MockResponse(json.dumps({"default_branch": "main"}).encode("utf-8"))
        assert headers["Accept"] == "application/vnd.github+json"
        return MockResponse(archive)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        materialized = materialize_source("owner/repo")

    if materialized.cleanup_root is not None:
        assert materialized.cleanup_root.exists()


def test_materialize_source_rejects_invalid_subpath() -> None:
    archive = github_archive_bytes(
        [
            (
                "owner-repo-main/SKILL.md",
                b"---\nname: demo-skill\ndescription: Demo skill\n---\n\nBody\n",
            )
        ]
    )

    def fake_urlopen(request: object, timeout: int = 60) -> MockResponse:
        url = request.full_url  # type: ignore[attr-defined]
        if url.endswith("/repos/owner/repo"):
            return MockResponse(json.dumps({"default_branch": "main"}).encode("utf-8"))
        return MockResponse(archive)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        with pytest.raises(SkillMgrError, match="does not exist"):
            materialize_source("owner/repo/skills/demo-skill")


def test_materialize_source_rejects_path_traversal_archive() -> None:
    archive = github_archive_bytes(
        [("../escape.txt", b"bad"), ("owner-repo-main/SKILL.md", b"ignored")]
    )

    def fake_urlopen(request: object, timeout: int = 60) -> MockResponse:
        url = request.full_url  # type: ignore[attr-defined]
        if url.endswith("/repos/owner/repo"):
            return MockResponse(json.dumps({"default_branch": "main"}).encode("utf-8"))
        return MockResponse(archive)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        with pytest.raises(SkillMgrError, match="invalid path"):
            materialize_source("owner/repo")


def test_materialize_source_uses_configured_api_base(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive = github_archive_bytes(
        [
            (
                "owner-repo-main/SKILL.md",
                b"---\nname: demo-skill\ndescription: Demo skill\n---\n\nBody\n",
            )
        ]
    )
    monkeypatch.setattr(
        "skill_mgr.sources.github.GITHUB_API_BASE", "https://example.test/api"
    )
    seen_urls: list[str] = []

    def fake_urlopen(request: object, timeout: int = 60) -> MockResponse:
        url = request.full_url  # type: ignore[attr-defined]
        seen_urls.append(url)
        if url.endswith("/repos/owner/repo"):
            return MockResponse(json.dumps({"default_branch": "main"}).encode("utf-8"))
        return MockResponse(archive)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        materialized = materialize_source("owner/repo")

    try:
        assert seen_urls == [
            "https://example.test/api/repos/owner/repo",
            "https://example.test/api/repos/owner/repo/tarball/main",
        ]
        assert materialized.cleanup_root is not None
    finally:
        if materialized.cleanup_root is not None:
            assert materialized.cleanup_root.exists()


def test_materialize_source_uses_github_token_when_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive = github_archive_bytes(
        [
            (
                "owner-repo-main/SKILL.md",
                b"---\nname: demo-skill\ndescription: Demo skill\n---\n\nBody\n",
            )
        ]
    )
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    auth_headers: list[str | None] = []

    def fake_urlopen(request: object, timeout: int = 60) -> MockResponse:
        url = request.full_url  # type: ignore[attr-defined]
        headers = request.headers  # type: ignore[attr-defined]
        auth_headers.append(headers.get("Authorization"))
        if url.endswith("/repos/owner/repo"):
            return MockResponse(json.dumps({"default_branch": "main"}).encode("utf-8"))
        return MockResponse(archive)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        materialized = materialize_source("owner/repo")

    try:
        assert auth_headers == ["Bearer test-token", "Bearer test-token"]
        assert materialized.cleanup_root is not None
    finally:
        if materialized.cleanup_root is not None:
            assert materialized.cleanup_root.exists()
