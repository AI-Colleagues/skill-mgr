from __future__ import annotations
from pathlib import Path
import pytest
from skill_mgr.cli import run
from tests.helpers import write_skill


def test_cli_validate_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    skill_dir = write_skill(tmp_path / "demo-skill")
    status = run(["validate", str(skill_dir)])
    captured = capsys.readouterr()
    assert status == 0
    assert '"valid": true' in captured.out


def test_cli_support_matrix_human(capsys: pytest.CaptureFixture[str]) -> None:
    status = run(["support-matrix", "--human"])
    captured = capsys.readouterr()
    assert status == 0
    assert "openclaw" in captured.out


def test_cli_invalid_source_returns_non_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = run(["validate", "./missing-skill"])
    captured = capsys.readouterr()
    assert status == 1
    assert "error" in captured.out.lower()
