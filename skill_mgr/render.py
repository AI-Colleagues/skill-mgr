"""Human-readable output helpers."""

from __future__ import annotations
import json
from typing import Any


def render_json(payload: Any) -> str:
    """Render JSON with stable indentation."""
    return json.dumps(payload, indent=2, sort_keys=False)


def _stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, list | dict):
        return json.dumps(value, ensure_ascii=True)
    return str(value)


def render_table(headers: list[str], rows: list[list[object]]) -> str:
    """Render a simple left-aligned table."""
    widths = [len(header) for header in headers]
    normalized_rows: list[list[str]] = []
    for row in rows:
        normalized = [_stringify(cell) for cell in row]
        normalized_rows.append(normalized)
        for index, value in enumerate(normalized):
            widths[index] = max(widths[index], len(value))

    lines: list[str] = [
        "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)),
        "  ".join("-" * width for width in widths),
    ]
    for normalized_row in normalized_rows:
        lines.append(
            "  ".join(
                value.ljust(widths[index])
                for index, value in enumerate(normalized_row)
            )
        )
    return "\n".join(lines)


def _render_action_payload(payload: dict[str, Any]) -> str:
    heading = f"{payload['action']} {payload.get('skill', '')}".strip()
    rows = [
        [
            target.get("target", ""),
            target.get("status", ""),
            target.get("path", ""),
            target.get("message", ""),
        ]
        for target in payload.get("targets", [])
    ]
    table = render_table(["Target", "Status", "Path", "Message"], rows)
    return f"{heading}\n\n{table}"


def _render_validate_payload(payload: dict[str, Any]) -> str:
    lines = [f"valid: {payload['valid']}", f"source: {payload['source']['kind']}"]
    skill = payload.get("skill")
    if skill is not None:
        lines.extend([f"name: {skill['name']}", f"description: {skill['description']}"])
    errors = payload.get("errors", [])
    if errors:
        rows = [[error["field"], error["code"], error["message"]] for error in errors]
        lines.extend(["", render_table(["Field", "Code", "Message"], rows)])
    return "\n".join(lines)


def _render_list_payload(payload: dict[str, Any]) -> str:
    blocks: list[str] = []
    for target in payload.get("targets", []):
        header = f"{target['target']} ({target['status']})"
        if target["status"] == "skipped_unavailable":
            blocks.append(f"{header}\n{target.get('message', '')}")
            continue
        rows = [
            [skill.get("name", ""), skill.get("description", ""), skill.get("path", "")]
            for skill in target.get("skills", [])
        ]
        body = (
            render_table(["Name", "Description", "Path"], rows)
            if rows
            else "No installed skills."
        )
        blocks.append(f"{header}\n{body}")
    return "\n\n".join(blocks)


def _render_show_payload(payload: dict[str, Any]) -> str:
    blocks = []
    for target in payload.get("targets", []):
        header = f"{target['target']} ({target['status']})"
        if target["status"] != "installed":
            blocks.append(f"{header}\n{target.get('message', '')}")
            continue
        metadata = target.get("metadata") or {}
        lines = [
            f"name: {metadata.get('name', '')}",
            f"description: {metadata.get('description', '')}",
            f"path: {target.get('path', '')}",
        ]
        blocks.append(f"{header}\n" + "\n".join(lines))
    return "\n\n".join(blocks)


def _render_support_matrix(payload: dict[str, Any]) -> str:
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
    return render_table(
        ["Adapter", "Windows", "Linux", "macOS", "Install Root", "Notes"],
        rows,
    )


def render_human(payload: dict[str, Any]) -> str:
    """Render a command payload in human form."""
    if "error" in payload:
        error = payload["error"]
        result = f"Error [{error['code']}]: {error['message']}"
    elif payload.get("action") in {"install", "update", "uninstall"}:
        result = _render_action_payload(payload)
    elif payload.get("valid") is not None:
        result = _render_validate_payload(payload)
    elif payload.get("action") == "list":
        result = _render_list_payload(payload)
    elif payload.get("action") == "show":
        result = _render_show_payload(payload)
    elif payload.get("action") == "support-matrix":
        result = _render_support_matrix(payload)
    else:
        result = render_json(payload)
    return result
