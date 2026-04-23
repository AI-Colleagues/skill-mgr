"""CLI output helpers."""

from __future__ import annotations
import json
import shutil
from io import StringIO
from typing import Any
from rich.console import Console
from rich.pretty import Pretty
from rich.table import Table


def render_json(payload: Any) -> str:
    """Render JSON with stable indentation."""
    return json.dumps(payload, indent=2, sort_keys=False)


def _stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, list | dict):
        return json.dumps(value, ensure_ascii=True)
    return str(value)


def render_markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    """Render a Markdown table."""
    header = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    lines = [header, separator]
    for row in rows:
        cells = [_stringify(cell).replace("|", "\\|") for cell in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _render_rich_table(
    console: Console,
    *,
    title: str | None,
    headers: list[str],
    rows: list[list[object]],
) -> None:
    if _use_stacked_rich_table(console.width, len(headers)):
        _render_rich_stacked_table(
            console,
            title=title,
            headers=headers,
            rows=rows,
        )
        return

    table = Table(title=title, show_lines=False)
    for header in headers:
        table.add_column(header, overflow="fold")
    for row in rows:
        table.add_row(*[_stringify(cell) for cell in row])
    console.print(table)


def _use_stacked_rich_table(width: int, column_count: int) -> bool:
    return (column_count >= 5 and width < 100) or (column_count >= 3 and width < 60)


def _render_rich_stacked_table(
    console: Console,
    *,
    title: str | None,
    headers: list[str],
    rows: list[list[object]],
) -> None:
    if title is not None:
        console.print(f"[bold]{title}[/bold]")
    for index, row in enumerate(rows):
        if index > 0:
            console.print()

        label = f"Row {index + 1}"
        if row and row[0]:  # pragma: no branch
            label = _stringify(row[0])

        if len(rows) > 1:
            console.print(f"[bold]{label}[/bold]")
        details = Table(
            show_header=False,
            show_lines=False,
            expand=True,
            pad_edge=False,
        )
        details.add_column("Field", style="bold", no_wrap=True)
        details.add_column("Value", overflow="fold")
        for header, cell in zip(headers, row, strict=True):
            details.add_row(header, _stringify(cell))
        console.print(details)


def _rich_console_width(width: int | None = None) -> int:
    if width is not None:
        return width
    return shutil.get_terminal_size(fallback=(120, 24)).columns


def _render_rich_action(console: Console, payload: dict[str, Any]) -> None:
    heading = f"{payload['action']} {payload.get('skill', '')}".strip()
    console.print(f"[bold]{heading}[/bold]")
    rows = [
        [
            target.get("target", ""),
            target.get("status", ""),
            target.get("message", ""),
        ]
        for target in payload.get("targets", [])
    ]
    _render_rich_table(
        console,
        title="Targets",
        headers=["Target", "Status", "Message"],
        rows=rows,
    )


def _render_rich_validate(console: Console, payload: dict[str, Any]) -> None:
    rows = [
        ["Valid", payload["valid"]],
        ["Source", payload["source"]["kind"]],
    ]
    skill = payload.get("skill")
    if skill is not None:
        rows.extend(
            [
                ["Name", skill["name"]],
                ["Description", skill["description"]],
            ]
        )
    _render_rich_table(
        console,
        title="Validation",
        headers=["Field", "Value"],
        rows=rows,
    )
    errors = payload.get("errors", [])
    if errors:
        error_rows = [
            [error["field"], error["code"], error["message"]] for error in errors
        ]
        _render_rich_table(
            console,
            title="Errors",
            headers=["Field", "Code", "Message"],
            rows=error_rows,
        )


def _render_rich_list(console: Console, payload: dict[str, Any]) -> None:
    def section_title(target: dict[str, Any]) -> str:
        skill_count = len(target.get("skills", []))
        skill_label = "1 skill" if skill_count == 1 else f"{skill_count} skills"
        if target["status"] == "skipped_unavailable":
            return f"{target['target']} ({target['status']})"
        return f"{target['target']} ({target['status']}, {skill_label})"

    console.print("[bold]Installed Skills[/bold]")
    for index, target in enumerate(payload.get("targets", [])):
        if index > 0:
            console.print()
        if target["status"] == "skipped_unavailable":
            console.print(f"[bold]{section_title(target)}[/bold]")
            console.print(target.get("message", ""))
            continue
        rows = [
            [
                skill.get("name", ""),
                skill.get("version", ""),
                skill.get("description", ""),
            ]
            for skill in target.get("skills", [])
        ]
        if rows:
            _render_rich_table(
                console,
                title=section_title(target),
                headers=["Name", "Version", "Description"],
                rows=rows,
            )
        else:
            console.print(f"[bold]{section_title(target)}[/bold]")
            console.print("No installed skills.")


def _render_rich_show(console: Console, payload: dict[str, Any]) -> None:
    console.print(f"[bold]Skill: {payload['name']}[/bold]")
    for target in payload.get("targets", []):
        console.print(f"[bold]{target['target']}[/bold] ({target['status']})")
        if target["status"] != "installed":
            console.print(target.get("message", ""))
            continue
        metadata = target.get("metadata") or {}
        rows = [
            ["Name", metadata.get("name", "")],
            ["Description", metadata.get("description", "")],
        ]
        _render_rich_table(console, title=None, headers=["Field", "Value"], rows=rows)


def _render_rich_support_matrix(console: Console, payload: dict[str, Any]) -> None:
    rows = [
        [
            row["adapter"],
            row["windows"],
            row["linux"],
            row["macos"],
            row["install_root"],
            row["notes"],
        ]
        for row in payload.get("targets", [])
    ]
    _render_rich_table(
        console,
        title="Support Matrix",
        headers=["Adapter", "Windows", "Linux", "macOS", "Install Root", "Notes"],
        rows=rows,
    )


def render_rich(payload: dict[str, Any], *, width: int | None = None) -> str:
    """Render a payload using Rich tables and pretty output."""
    console = Console(
        record=True,
        force_terminal=False,
        width=_rich_console_width(width),
        file=StringIO(),
    )
    if "error" in payload:
        error = payload["error"]
        console.print(
            f"[bold red]Error [{error['code']}] [/bold red]{error['message']}"
        )
    elif payload.get("action") in {"install", "update", "uninstall"}:
        _render_rich_action(console, payload)
    elif payload.get("action") == "validate" or payload.get("valid") is not None:
        _render_rich_validate(console, payload)
    elif payload.get("action") == "list":
        _render_rich_list(console, payload)
    elif payload.get("action") == "show":
        _render_rich_show(console, payload)
    elif payload.get("action") == "support-matrix":
        _render_rich_support_matrix(console, payload)
    else:
        console.print(Pretty(payload, indent_guides=True))
    return console.export_text()


def _render_markdown_action(payload: dict[str, Any]) -> str:
    heading = f"## {payload['action']} {payload.get('skill', '')}".strip()
    rows = [
        [
            target.get("target", ""),
            target.get("status", ""),
            target.get("message", ""),
        ]
        for target in payload.get("targets", [])
    ]
    table = render_markdown_table(["Target", "Status", "Message"], rows)
    return f"{heading}\n\n{table}"


def _render_markdown_validate(payload: dict[str, Any]) -> str:
    lines = [
        "## Validation",
        f"- valid: {payload['valid']}",
        f"- source: {payload['source']['kind']}",
    ]
    skill = payload.get("skill")
    if skill is not None:
        lines.extend(
            [
                f"- name: {skill['name']}",
                f"- description: {skill['description']}",
            ]
        )
    errors = payload.get("errors", [])
    if errors:
        rows = [[error["field"], error["code"], error["message"]] for error in errors]
        lines.extend(
            [
                "",
                "### Errors",
                "",
                render_markdown_table(["Field", "Code", "Message"], rows),
            ]
        )
    return "\n".join(lines)


def _render_markdown_list(payload: dict[str, Any]) -> str:
    blocks = ["## Installed Skills"]
    for target in payload.get("targets", []):
        skill_count = len(target.get("skills", []))
        skill_label = "1 skill" if skill_count == 1 else f"{skill_count} skills"
        if target["status"] == "skipped_unavailable":
            blocks.append(f"\n### {target['target']} ({target['status']})")
        else:
            blocks.append(
                f"\n### {target['target']} ({target['status']}, {skill_label})"
            )
        if target["status"] == "skipped_unavailable":
            blocks.append(target.get("message", ""))
            continue
        rows = [
            [
                skill.get("name", ""),
                skill.get("version", ""),
                skill.get("description", ""),
            ]
            for skill in target.get("skills", [])
        ]
        if rows:
            blocks.append(
                render_markdown_table(["Name", "Version", "Description"], rows)
            )
        else:
            blocks.append("No installed skills.")
    return "\n".join(blocks)


def _render_markdown_show(payload: dict[str, Any]) -> str:
    blocks = [f"## Skill: {payload['name']}"]
    for target in payload.get("targets", []):
        blocks.append(f"\n### {target['target']} ({target['status']})")
        if target["status"] != "installed":
            blocks.append(target.get("message", ""))
            continue
        metadata = target.get("metadata") or {}
        rows = [
            ["Name", metadata.get("name", "")],
            ["Description", metadata.get("description", "")],
        ]
        blocks.append(render_markdown_table(["Field", "Value"], rows))
    return "\n".join(blocks)


def _render_markdown_support_matrix(payload: dict[str, Any]) -> str:
    rows = [
        [
            row["adapter"],
            row["windows"],
            row["linux"],
            row["macos"],
            row["install_root"],
            row["notes"],
        ]
        for row in payload.get("targets", [])
    ]
    table = render_markdown_table(
        ["Adapter", "Windows", "Linux", "macOS", "Install Root", "Notes"],
        rows,
    )
    return f"## Support Matrix\n\n{table}"


def render_markdown(payload: dict[str, Any]) -> str:
    """Render a command payload as Markdown."""
    result: str
    if "error" in payload:
        error = payload["error"]
        result = "\n".join(
            ["## Error", f"- code: {error['code']}", f"- message: {error['message']}"]
        )
    elif payload.get("action") in {"install", "update", "uninstall"}:
        result = _render_markdown_action(payload)
    elif payload.get("action") == "validate" or payload.get("valid") is not None:
        result = _render_markdown_validate(payload)
    elif payload.get("action") == "list":
        result = _render_markdown_list(payload)
    elif payload.get("action") == "show":
        result = _render_markdown_show(payload)
    elif payload.get("action") == "support-matrix":
        result = _render_markdown_support_matrix(payload)
    else:
        result = f"```json\n{render_json(payload)}\n```"
    return result
