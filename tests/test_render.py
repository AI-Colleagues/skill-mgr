from __future__ import annotations
from io import StringIO
from rich.console import Console
from skill_mgr.render import (
    _render_markdown_validate,
    _render_rich_validate,
    _stringify,
    render_markdown,
    render_rich,
)


def _list_payload() -> dict[str, object]:
    return {
        "action": "list",
        "targets": [
            {
                "target": "claude",
                "status": "available",
                "message": None,
                "skills": [
                    {
                        "name": "orcheo",
                        "description": "Orcheo workflow helper",
                        "path": "/tmp/.claude/skills/orcheo",
                    }
                ],
            },
            {
                "target": "codex",
                "status": "available",
                "message": None,
                "skills": [
                    {
                        "name": "data-coffee",
                        "description": "Data Coffee helper",
                        "path": "/tmp/.codex/skills/data-coffee",
                    },
                    {
                        "name": "orcheo",
                        "description": "Orcheo workflow helper",
                        "path": "/tmp/.codex/skills/orcheo",
                    },
                ],
            },
            {
                "target": "openclaw",
                "status": "skipped_unavailable",
                "message": "agent_not_detected",
                "skills": [],
            },
            {
                "target": "orcheo",
                "status": "available",
                "message": None,
                "skills": [],
            },
        ],
    }


def test_stringify_handles_special_values() -> None:
    assert _stringify(None) == ""
    assert _stringify([1, 2]) == "[1, 2]"
    assert _stringify({"a": 1}) == '{"a": 1}'


def test_render_rich_list_uses_agent_section_titles() -> None:
    output = render_rich(_list_payload())

    assert "Installed Skills" in output
    assert "claude (available, 1 skill)" in output
    assert "codex (available, 2 skills)" in output
    assert "openclaw (skipped_unavailable)" in output
    assert "orcheo (available, 0 skills)" in output
    assert "Name" in output
    assert "Description" in output
    assert "Path" in output
    assert "No installed skills." in output
    assert "agent_not_detected" in output


def test_render_markdown_list_uses_agent_section_titles() -> None:
    output = render_markdown(_list_payload())

    assert "## Installed Skills" in output
    assert "### claude (available, 1 skill)" in output
    assert "### codex (available, 2 skills)" in output
    assert "### openclaw (skipped_unavailable)" in output
    assert "### orcheo (available, 0 skills)" in output
    assert "| Name | Description | Path |" in output
    assert "No installed skills." in output
    assert "agent_not_detected" in output


def test_render_rich_error_payload() -> None:
    output = render_rich({"error": {"code": "fail", "message": "boom"}})
    assert "Error" in output
    assert "boom" in output


def test_render_rich_validate_payload_with_errors() -> None:
    payload = {
        "action": "validate",
        "valid": False,
        "source": {"kind": "local"},
        "skill": {"name": "demo", "description": "desc"},
        "errors": [
            {"field": "name", "code": "invalid", "message": "oops"},
        ],
    }
    output = render_rich(payload)
    assert "Validation" in output
    assert "Errors" in output
    assert "demo" in output


def test_render_rich_action_payload() -> None:
    payload = {
        "action": "install",
        "skill": "demo",
        "targets": [
            {"target": "claude", "status": "installed", "path": "/tmp", "message": ""}
        ],
    }
    output = render_rich(payload)
    assert "install" in output
    assert "Targets" in output


def test_render_rich_show_and_support_matrix_variants() -> None:
    payload = {
        "action": "show",
        "name": "demo",
        "targets": [
            {
                "target": "claude",
                "status": "not_installed",
                "path": "/tmp/demo",
                "message": "missing",
            },
            {
                "target": "codex",
                "status": "installed",
                "path": "/tmp/demo",
                "metadata": {"name": "demo", "description": "desc"},
            },
        ],
    }
    output = render_rich(payload)
    assert "Skill: demo" in output
    assert "missing" in output
    support_payload = {
        "action": "support-matrix",
        "targets": [
            {
                "adapter": "claude",
                "windows": "supported",
                "linux": "supported",
                "macos": "supported",
                "install_root": "/tmp/.claude/skills",
                "notes": "notes",
            }
        ],
    }
    matrix_output = render_rich(support_payload)
    assert "Support Matrix" in matrix_output
    assert "claude" in matrix_output


def test_render_rich_defaults_to_pretty() -> None:
    output = render_rich({"foo": "bar"})
    assert "foo" in output


def test_render_markdown_error_payload() -> None:
    text = render_markdown({"error": {"code": "boom", "message": "bad"}})
    assert "## Error" in text
    assert "- code: boom" in text


def test_render_markdown_action_payload() -> None:
    payload = {
        "action": "install",
        "skill": "demo",
        "targets": [
            {"target": "claude", "status": "installed", "path": "/tmp", "message": ""}
        ],
    }
    result = render_markdown(payload)
    assert "## install" in result
    assert "| Target | Status | Path | Message |" in result


def test_render_markdown_validate_with_errors() -> None:
    payload = {
        "action": "validate",
        "valid": False,
        "source": {"kind": "local"},
        "skill": {"name": "demo", "description": "desc"},
        "errors": [{"field": "name", "code": "err", "message": "oops"}],
    }
    text = render_markdown(payload)
    assert "### Errors" in text
    assert "| Field | Code | Message |" in text
    assert "- name: demo" in text
    assert "- description: desc" in text


def test_render_markdown_show_and_support_matrix() -> None:
    payload = {
        "action": "show",
        "name": "demo",
        "targets": [
            {"target": "claude", "status": "not_installed", "message": "missing"},
            {
                "target": "codex",
                "status": "installed",
                "path": "/tmp/demo",
                "metadata": {"name": "demo", "description": "desc"},
            },
        ],
    }
    text = render_markdown(payload)
    assert "## Skill: demo" in text
    assert "### codex (installed)" in text
    support_payload = {
        "action": "support-matrix",
        "targets": [
            {
                "adapter": "claude",
                "windows": "supported",
                "linux": "supported",
                "macos": "supported",
                "install_root": "/tmp/.claude/skills",
                "notes": "notes",
            }
        ],
    }
    support_text = render_markdown(support_payload)
    assert "## Support Matrix" in support_text


def test_render_markdown_fallbacks_to_code_block() -> None:
    text = render_markdown({"message": "hello"})
    assert text.startswith("```json")


def test_render_rich_validate_helper_includes_skill_and_errors() -> None:
    console = Console(record=True, force_terminal=False, width=80, file=StringIO())
    payload = {
        "valid": False,
        "source": {"kind": "local"},
        "skill": {"name": "demo", "description": "desc"},
        "errors": [{"field": "name", "code": "invalid", "message": "oops"}],
    }
    _render_rich_validate(console, payload)
    output = console.export_text()
    assert "Validation" in output
    assert "Name" in output


def test_render_markdown_validate_helper_outputs_skill_and_errors() -> None:
    payload = {
        "valid": False,
        "source": {"kind": "local"},
        "skill": {"name": "demo", "description": "desc"},
        "errors": [{"field": "name", "code": "invalid", "message": "oops"}],
    }
    text = _render_markdown_validate(payload)
    assert "- name: demo" in text
    assert "### Errors" in text


def test_render_rich_validate_helper_handles_missing_skill_and_errors() -> None:
    console = Console(record=True, force_terminal=False, width=80, file=StringIO())
    payload = {"valid": True, "source": {"kind": "local"}}
    _render_rich_validate(console, payload)
    output = console.export_text()
    assert "Validation" in output
    assert "Errors" not in output


def test_render_markdown_validate_helper_handles_missing_skill_and_errors() -> None:
    payload = {"valid": True, "source": {"kind": "local"}}
    text = _render_markdown_validate(payload)
    assert "- name:" not in text
    assert "### Errors" not in text
