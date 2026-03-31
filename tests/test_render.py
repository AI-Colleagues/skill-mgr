from __future__ import annotations
from skill_mgr.render import render_markdown, render_rich


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
