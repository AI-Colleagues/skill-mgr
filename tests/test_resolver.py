from __future__ import annotations
from pathlib import Path
import pytest
from skill_mgr.errors import SkillMgrError
from skill_mgr.sources.resolver import materialize_source


def test_materialize_source_rejects_non_directory_local(tmp_path: Path) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("content", encoding="utf-8")
    with pytest.raises(SkillMgrError, match="is not a directory"):
        materialize_source(str(file_path))


def test_materialize_source_rejects_invalid_shorthand() -> None:
    with pytest.raises(SkillMgrError, match="does not exist locally"):
        materialize_source("just_one_segment")
