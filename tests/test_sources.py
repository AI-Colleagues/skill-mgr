from __future__ import annotations
import io
import json
import tarfile
import urllib.error
from pathlib import Path
from unittest.mock import patch
import pytest
from skill_mgr.errors import SkillMgrError
from skill_mgr.models import SourceDescriptor
from skill_mgr.sources import materialize_source, parse_github_shorthand
from skill_mgr.sources.github import (
    _extract_tarball,
    _repo_archive_url,
    _request_headers,
    _urlopen,
    materialize_github_source,
)
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


def test_parse_github_shorthand_rejects_invalid_values() -> None:
    for invalid in ["", "owner/", "owner/..", "owner/ repo", "owner\\repo"]:
        assert parse_github_shorthand(invalid) is None


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


def test_request_headers_include_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "token-value")
    headers = _request_headers(accept="application/json")
    assert headers["Authorization"] == "Bearer token-value"
    assert headers["Accept"] == "application/json"


def test_request_headers_exclude_token_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    headers = _request_headers(accept="application/json")
    assert "Authorization" not in headers


def test_urlopen_maps_http_error_codes(monkeypatch: pytest.MonkeyPatch) -> None:
    def make_error(code: int):
        def inner(*args: object, **kwargs: object) -> None:
            raise urllib.error.HTTPError(
                "http://example", code, "msg", hdrs=None, fp=None
            )

        return inner

    for code, expected in [
        (404, "github_not_found"),
        (403, "github_rate_limited"),
        (500, "github_download_failed"),
    ]:
        monkeypatch.setattr(
            "skill_mgr.sources.github.urllib.request.urlopen",
            make_error(code),
        )
        with pytest.raises(SkillMgrError) as exc:
            _urlopen("http://example")
        assert exc.value.code == expected


def test_urlopen_handles_timeout_and_url_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "skill_mgr.sources.github.urllib.request.urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError("sleep")),
    )
    with pytest.raises(SkillMgrError) as exc:
        _urlopen("http://example")
    assert exc.value.code == "github_timeout"

    monkeypatch.setattr(
        "skill_mgr.sources.github.urllib.request.urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(urllib.error.URLError("fail")),
    )
    with pytest.raises(SkillMgrError) as exc:
        _urlopen("http://example")
    assert exc.value.code == "github_download_failed"


def test_repo_archive_url_requires_default_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "skill_mgr.sources.github._request", lambda url, accept="": b"{}"
    )
    with pytest.raises(SkillMgrError, match="did not report a default branch"):
        _repo_archive_url("owner/repo")


def test_extract_tarball_rejects_symlink(tmp_path: Path) -> None:
    archive_path = tmp_path / "archive.tar.gz"
    with tarfile.open(archive_path, mode="w:gz") as archive:
        info = tarfile.TarInfo("link")
        info.type = tarfile.SYMTYPE
        info.linkname = "target"
        archive.addfile(info)

    with pytest.raises(SkillMgrError, match="unsupported links"):
        _extract_tarball(archive_path, tmp_path)


def test_extract_tarball_rejects_unexpected_layout(tmp_path: Path) -> None:
    archive_path = tmp_path / "layout.tar.gz"
    base = tmp_path / "base"
    (base / "first").mkdir(parents=True)
    (base / "second").mkdir(parents=True)
    with tarfile.open(archive_path, mode="w:gz") as archive:
        archive.add(base / "first", arcname="first")
        archive.add(base / "second", arcname="second")

    with pytest.raises(SkillMgrError, match="unexpected layout"):
        _extract_tarball(archive_path, tmp_path)


def test_materialize_github_source_rejects_missing_repository() -> None:
    descriptor = SourceDescriptor(kind="github", ref="owner/repo", repository=None)
    with pytest.raises(SkillMgrError, match="missing a repository"):
        materialize_github_source(descriptor)


def test_materialize_github_source_rejects_absolute_subpath(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.setattr(
        "skill_mgr.sources.github._repo_archive_url",
        lambda repository: "https://example",
    )
    monkeypatch.setattr(
        "skill_mgr.sources.github._download_to_file",
        lambda url, destination, accept="": destination.write_bytes(b""),
    )
    monkeypatch.setattr(
        "skill_mgr.sources.github._extract_tarball",
        lambda archive_path, destination: repo_root,
    )
    descriptor = SourceDescriptor(
        kind="github",
        ref="owner/repo",
        repository="owner/repo",
        subpath="/abs",
    )
    with pytest.raises(SkillMgrError, match="must be relative"):
        materialize_github_source(descriptor)
