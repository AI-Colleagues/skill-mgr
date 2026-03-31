from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from skill_mgr.cli import app, run
from tests.helpers import write_skill


def test_cli_root_help_short_flag() -> None:
    result = CliRunner().invoke(app, ["-h"], prog_name="skill-mgr")
    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "skill-mgr" in result.output


def test_cli_command_help_short_flag() -> None:
    result = CliRunner().invoke(app, ["list", "-h"])
    assert result.exit_code == 0
    assert "List installed skills" in result.output


def test_cli_support_matrix_rich_is_not_duplicated(
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = run(["support-matrix"])
    captured = capsys.readouterr()
    assert status == 0
    assert captured.out.count("Support Matrix") == 1


def test_cli_validate_uses_rich_by_default(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skill_dir = write_skill(tmp_path / "demo-skill")
    status = run(["validate", str(skill_dir)])
    captured = capsys.readouterr()
    assert status == 0
    assert "Validation" in captured.out
    assert "demo-skill" in captured.out


def test_cli_support_matrix_markdown(capsys: pytest.CaptureFixture[str]) -> None:
    status = run(["support-matrix", "--format", "markdown"])
    captured = capsys.readouterr()
    assert status == 0
    assert "| Adapter |" in captured.out
    assert "orcheo" in captured.out


def test_cli_validate_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    skill_dir = write_skill(tmp_path / "demo-skill")
    status = run(["validate", str(skill_dir), "--format", "json"])
    captured = capsys.readouterr()
    assert status == 0
    assert '"valid": true' in captured.out


def test_cli_support_matrix_rich(capsys: pytest.CaptureFixture[str]) -> None:
    status = run(["support-matrix"])
    captured = capsys.readouterr()
    assert status == 0
    assert "Support Matrix" in captured.out
    assert "openclaw" in captured.out
    assert "orcheo" in captured.out


def test_cli_invalid_source_returns_non_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = run(["validate", "./missing-skill"])
    captured = capsys.readouterr()
    assert status == 1
    assert "error" in captured.out.lower()
