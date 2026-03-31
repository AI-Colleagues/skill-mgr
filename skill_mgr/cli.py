"""Command-line interface."""

from __future__ import annotations

import sys
from collections.abc import Callable
from enum import StrEnum
from typing import Annotated, Any

import typer
from typer.testing import CliRunner

from skill_mgr.adapters import bundled_adapter_matrix
from skill_mgr.errors import SkillMgrError
from skill_mgr.render import render_json, render_markdown, render_rich
from skill_mgr.services import SkillManagerService


HELP_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}

app = typer.Typer(
    help="Install, inspect, and manage agent skills.",
    context_settings=HELP_CONTEXT_SETTINGS,
)


class OutputFormat(StrEnum):
    """Supported CLI output formats."""

    RICH = "rich"
    MARKDOWN = "markdown"
    JSON = "json"


FormatOption = Annotated[
    OutputFormat,
    typer.Option(
        "--format",
        help=(
            "Output format. `rich` is the default human-friendly mode, "
            "`markdown` is plain-text and LLM-friendly, and `json` is structured."
        ),
        case_sensitive=False,
    ),
]
TargetOption = Annotated[
    list[str] | None,
    typer.Option(
        "--target",
        "-t",
        help="Target agent. Repeat for multiple targets or use `all`.",
    ),
]


def _emit(payload: dict[str, Any], *, output_format: OutputFormat) -> None:
    if output_format == OutputFormat.JSON:
        typer.echo(render_json(payload))
        return
    if output_format == OutputFormat.MARKDOWN:
        typer.echo(render_markdown(payload))
        return
    typer.echo(render_rich(payload), nl=False)


def _exit_status(command: str, payload: dict[str, Any]) -> int:
    if command == "validate":
        return 0 if payload["valid"] else 1
    if any(target.get("status") == "error" for target in payload.get("targets", [])):
        return 1
    return 0


def _run_command(
    command: str,
    *,
    output_format: OutputFormat,
    operation: Callable[[], dict[str, Any]],
) -> None:
    try:
        payload = operation()
    except SkillMgrError as exc:
        _emit(
            {"error": {"code": exc.code, "message": str(exc)}},
            output_format=output_format,
        )
        raise typer.Exit(code=1) from exc

    _emit(payload, output_format=output_format)
    exit_code = _exit_status(command, payload)
    if exit_code:
        raise typer.Exit(code=exit_code)


@app.command("install", context_settings=HELP_CONTEXT_SETTINGS)
def install(
    ref: str,
    target: TargetOption = None,
    output_format: FormatOption = OutputFormat.RICH,
) -> None:
    """Install a skill across one or more targets."""
    service = SkillManagerService()
    _run_command(
        "install",
        output_format=output_format,
        operation=lambda: service.install(ref, targets=target),
    )


@app.command("update", context_settings=HELP_CONTEXT_SETTINGS)
def update(
    ref: str,
    target: TargetOption = None,
    output_format: FormatOption = OutputFormat.RICH,
) -> None:
    """Update a skill across one or more targets."""
    service = SkillManagerService()
    _run_command(
        "update",
        output_format=output_format,
        operation=lambda: service.update(ref, targets=target),
    )


@app.command("uninstall", context_settings=HELP_CONTEXT_SETTINGS)
def uninstall(
    name: str,
    target: TargetOption = None,
    output_format: FormatOption = OutputFormat.RICH,
) -> None:
    """Uninstall a skill across one or more targets."""
    service = SkillManagerService()
    _run_command(
        "uninstall",
        output_format=output_format,
        operation=lambda: service.uninstall(name, targets=target),
    )


@app.command("validate", context_settings=HELP_CONTEXT_SETTINGS)
def validate(
    ref: str,
    output_format: FormatOption = OutputFormat.RICH,
) -> None:
    """Validate a skill source without installing it."""
    service = SkillManagerService()
    _run_command(
        "validate",
        output_format=output_format,
        operation=lambda: service.validate(ref),
    )


@app.command("list", context_settings=HELP_CONTEXT_SETTINGS)
def list_skills(
    target: TargetOption = None,
    output_format: FormatOption = OutputFormat.RICH,
) -> None:
    """List installed skills across one or more targets."""
    service = SkillManagerService()
    _run_command(
        "list",
        output_format=output_format,
        operation=lambda: service.list(targets=target),
    )


@app.command("show", context_settings=HELP_CONTEXT_SETTINGS)
def show(
    name: str,
    target: TargetOption = None,
    output_format: FormatOption = OutputFormat.RICH,
) -> None:
    """Show one installed skill across one or more targets."""
    service = SkillManagerService()
    _run_command(
        "show",
        output_format=output_format,
        operation=lambda: service.show(name, targets=target),
    )


@app.command("support-matrix", context_settings=HELP_CONTEXT_SETTINGS)
def support_matrix(
    output_format: FormatOption = OutputFormat.RICH,
) -> None:
    """Show the bundled adapter support matrix."""
    _run_command(
        "support-matrix",
        output_format=output_format,
        operation=bundled_adapter_matrix,
    )


def run(argv: list[str] | None = None) -> int:
    """Run the CLI and return an exit status."""
    runner = CliRunner()
    result = runner.invoke(app, argv or [], prog_name="skill-mgr")
    sys.stdout.write(result.output)
    return result.exit_code
