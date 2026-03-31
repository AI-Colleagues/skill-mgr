from __future__ import annotations
from pathlib import Path
from skill_mgr.models import (
    AgentAdapter,
    SkillMetadata,
    SourceDescriptor,
    ValidationError,
)


def test_skill_metadata_to_dict_includes_extra_fields() -> None:
    metadata = SkillMetadata(
        name="demo",
        description="Description",
        license="MIT",
        compatibility="main",
        metadata={"key": "value"},
        allowed_tools="tool",
        extra_fields={"notes": "custom"},
    )

    data = metadata.to_dict()
    assert data["name"] == "demo"
    assert data["license"] == "MIT"
    assert data["extra_fields"] == {"notes": "custom"}


def test_validation_error_to_dict() -> None:
    error = ValidationError(code="missing", field="name", message="Name required")
    assert error.to_dict() == {
        "code": "missing",
        "field": "name",
        "message": "Name required",
    }


def test_source_descriptor_to_dict_handles_optional_fields() -> None:
    descriptor = SourceDescriptor(
        kind="github",
        ref="owner/repo",
        path="/tmp/owner",
        repository="owner/repo",
        subpath="skills/demo",
    )

    data = descriptor.to_dict()
    assert data["path"] == "/tmp/owner"
    assert data["repository"] == "owner/repo"
    assert data["subpath"] == "skills/demo"

    minimal = SourceDescriptor(kind="local", ref="/tmp/demo")
    minimal_data = minimal.to_dict()
    assert "path" not in minimal_data


def test_agent_adapter_to_dict_includes_paths() -> None:
    adapter = AgentAdapter(
        name="custom",
        support_by_os={"linux": "supported"},
        install_root_by_os={"linux": "/tmp/custom"},
        detection_root_by_os={"linux": "/tmp/custom"},
        current_os="linux",
        install_root=Path("/tmp/custom"),
        detection_root=Path("/tmp/custom"),
        available=True,
        availability_reason="ok",
    )

    data = adapter.to_dict()
    assert Path(data["install_root"]).as_posix() == "/tmp/custom"
    assert Path(data["detection_root"]).as_posix() == "/tmp/custom"
    assert data["available"] is True
