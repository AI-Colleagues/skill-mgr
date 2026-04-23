from __future__ import annotations
from pathlib import Path
from typing import cast
import pytest
import typer
from typer.testing import CliRunner
from skill_mgr.cli import (
    OutputFormat,
    _emit,
    _exit_status,
    _run_command,
    app,
    install,
    list_skills,
    show,
    support_matrix,
    uninstall,
    update,
    validate,
)
from skill_mgr.errors import SkillMgrError
from tests.helpers import run, write_skill


def test_cli_root_help_short_flag() -> None:
    result = CliRunner().invoke(app, ["-h"], prog_name="skill-mgr")
    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "skill-mgr" in result.output


def test_cli_root_version_long_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("skill_mgr.cli._cli_version", lambda: "1.2.3")
    result = CliRunner().invoke(app, ["--version"], prog_name="skill-mgr")
    assert result.exit_code == 0
    assert result.output == "1.2.3\n"


def test_cli_root_version_short_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("skill_mgr.cli._cli_version", lambda: "1.2.3")
    result = CliRunner().invoke(app, ["-v"], prog_name="skill-mgr")
    assert result.exit_code == 0
    assert result.output == "1.2.3\n"


def test_cli_version_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib.metadata as importlib_metadata

    def fake_version(name: str) -> str:
        raise importlib_metadata.PackageNotFoundError

    monkeypatch.setattr("importlib.metadata.version", fake_version)
    # We need to clear the cache if any, but _cli_version doesn't seem to cache.
    # Wait, _cli_version is called by _version_callback.
    from skill_mgr.cli import _cli_version

    assert _cli_version() == "unknown"


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


def test_emit_dispatches_to_render_functions(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, bool]] = []

    def fake_echo(value: str, **kwargs: object) -> None:
        calls.append((value, kwargs.get("nl", True)))  # type: ignore[arg-type]

    monkeypatch.setattr("typer.echo", fake_echo)
    monkeypatch.setattr("skill_mgr.cli.render_json", lambda payload: "json-payload")
    monkeypatch.setattr(
        "skill_mgr.cli.render_markdown", lambda payload: "markdown-payload"
    )
    monkeypatch.setattr("skill_mgr.cli.render_rich", lambda payload: "rich-payload")

    _emit({"a": 1}, output_format=OutputFormat.JSON)
    _emit({"b": 2}, output_format=OutputFormat.MARKDOWN)
    _emit({"c": 3}, output_format=OutputFormat.RICH)

    assert calls == [
        ("json-payload", True),
        ("markdown-payload", True),
        ("rich-payload", False),
    ]


def test_exit_status_checks_payloads() -> None:
    assert _exit_status("validate", {"valid": True}) == 0
    assert _exit_status("validate", {"valid": False}) == 1
    assert _exit_status("show", {"targets": [{"status": "error"}]}) == 1
    assert _exit_status("show", {"targets": [{"status": "installed"}]}) == 0


def test_run_command_raises_on_operation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    emitted: list[dict[str, object]] = []

    def fake_emit(payload: dict[str, object], *, output_format: OutputFormat) -> None:
        emitted.append(payload)

    monkeypatch.setattr("skill_mgr.cli._emit", fake_emit)

    def failing_operation() -> dict[str, object]:
        raise SkillMgrError("boom", code="boom")

    with pytest.raises(typer.Exit) as excinfo:
        _run_command(
            "validate", output_format=OutputFormat.JSON, operation=failing_operation
        )
    assert excinfo.value.exit_code == 1
    assert emitted
    error_payload = cast(dict[str, str], emitted[0]["error"])
    assert error_payload["code"] == "boom"


def test_run_command_raises_on_exit_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("skill_mgr.cli._emit", lambda payload, *, output_format: None)
    monkeypatch.setattr("skill_mgr.cli._exit_status", lambda command, payload: 2)

    with pytest.raises(typer.Exit) as excinfo:
        _run_command(
            "install", output_format=OutputFormat.RICH, operation=lambda: {"ok": True}
        )
    assert excinfo.value.exit_code == 2


def test_cli_command_wrappers_use_run_command(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_run(command: str, **kwargs: object) -> None:
        calls.append(command)

    monkeypatch.setattr("skill_mgr.cli._run_command", fake_run)
    install("ref")
    update("ref")
    uninstall("name")
    validate("ref")
    list_skills()
    show("name")
    support_matrix()

    assert calls == [
        "install",
        "update",
        "uninstall",
        "validate",
        "list",
        "show",
        "support-matrix",
    ]
