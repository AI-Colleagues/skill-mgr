"""GitHub shorthand parsing and archive materialization."""

from __future__ import annotations
import json
import os
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath
from skill_mgr.errors import SkillMgrError
from skill_mgr.models import MaterializedSource, SourceDescriptor


GITHUB_API_BASE = "https://api.github.com"


def parse_github_shorthand(ref: str) -> SourceDescriptor | None:
    """Parse ``owner/repo[/path]`` shorthand."""
    normalized = ref.strip().strip("/")
    if not normalized or "\\" in normalized or " " in normalized:
        return None
    parts = normalized.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        return None
    if any(part in {".", "..", ""} for part in parts):
        return None
    subpath = "/".join(parts[2:]) or None
    return SourceDescriptor(
        kind="github",
        ref=ref,
        repository=f"{parts[0]}/{parts[1]}",
        subpath=subpath,
    )


def _request_headers(*, accept: str) -> dict[str, str]:
    headers = {
        "Accept": accept,
        "User-Agent": "skill-mgr/0.0.1",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _urlopen(url: str, *, accept: str = "application/vnd.github+json"):
    request = urllib.request.Request(url, headers=_request_headers(accept=accept))
    try:
        return urllib.request.urlopen(request, timeout=60)
    except urllib.error.HTTPError as exc:
        code = "github_download_failed"
        if exc.code == 404:
            code = "github_not_found"
        elif exc.code == 403:
            code = "github_rate_limited"
        raise SkillMgrError(
            f"GitHub request failed for '{url}' with status {exc.code}.",
            code=code,
        ) from exc
    except TimeoutError as exc:
        raise SkillMgrError(
            f"GitHub request timed out for '{url}'.",
            code="github_timeout",
        ) from exc
    except urllib.error.URLError as exc:
        raise SkillMgrError(
            f"GitHub request failed for '{url}'.",
            code="github_download_failed",
        ) from exc


def _request(url: str, *, accept: str = "application/vnd.github+json") -> bytes:
    with _urlopen(url, accept=accept) as response:
        return response.read()


def _download_to_file(
    url: str, destination: Path, *, accept: str = "application/vnd.github+json"
) -> None:
    with _urlopen(url, accept=accept) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def _repo_archive_url(repository: str) -> str:
    payload = json.loads(
        _request(f"{GITHUB_API_BASE}/repos/{repository}").decode("utf-8")
    )
    default_branch = payload.get("default_branch")
    if not isinstance(default_branch, str) or not default_branch:
        raise SkillMgrError(
            f"GitHub repository '{repository}' did not report a default branch.",
            code="github_bad_metadata",
        )
    return f"{GITHUB_API_BASE}/repos/{repository}/tarball/{default_branch}"


def _extract_tarball(archive_path: Path, destination_root: Path) -> Path:
    extracted_root = destination_root / "extract"
    extracted_root.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, mode="r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            if member.issym() or member.islnk():
                raise SkillMgrError(
                    "Downloaded GitHub archive contains unsupported links.",
                    code="invalid_archive_link",
                )
            target_path = (extracted_root / member.name).resolve()
            if (
                target_path != extracted_root.resolve()
                and extracted_root.resolve() not in target_path.parents
            ):
                raise SkillMgrError(
                    "Downloaded GitHub archive contains an invalid path.",
                    code="invalid_archive_path",
                )
        archive.extractall(extracted_root, members=members, filter="data")

    top_level_dirs = [path for path in extracted_root.iterdir() if path.is_dir()]
    if len(top_level_dirs) != 1:
        raise SkillMgrError(
            "Downloaded GitHub archive has an unexpected layout.",
            code="invalid_archive_layout",
        )
    return top_level_dirs[0]


def materialize_github_source(source: SourceDescriptor) -> MaterializedSource:
    """Download and extract a GitHub shorthand source."""
    if source.repository is None:
        raise SkillMgrError(
            "GitHub source is missing a repository.", code="invalid_source"
        )

    temp_root = Path(tempfile.mkdtemp(prefix="skill-mgr-source-"))
    try:
        archive_path = temp_root / "source.tar.gz"
        _download_to_file(_repo_archive_url(source.repository), archive_path)
        repo_root = _extract_tarball(archive_path, temp_root)
        skill_dir = repo_root
        if source.subpath is not None:
            relative = PurePosixPath(source.subpath)
            if relative.is_absolute():
                raise SkillMgrError(
                    f"GitHub subpath '{source.subpath}' must be relative.",
                    code="invalid_subpath",
                )
            skill_dir = repo_root.joinpath(*relative.parts)
        if not skill_dir.exists() or not skill_dir.is_dir():
            raise SkillMgrError(
                "GitHub subpath "
                f"'{source.subpath or '.'}' does not exist in "
                f"{source.repository}.",
                code="invalid_subpath",
            )
        return MaterializedSource(
            source=source, directory=skill_dir, cleanup_root=temp_root
        )
    except Exception:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise
