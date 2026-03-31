from __future__ import annotations
import runpy
import sys
from skill_mgr.main import main


def test_main_calls_app(monkeypatch) -> None:
    calls: list[str] = []

    def fake_app(prog_name: str) -> None:
        calls.append(prog_name)

    monkeypatch.setattr("skill_mgr.main.app", fake_app)
    main()
    assert calls == ["skill-mgr"]


def test_main_entry_point_runs_app(monkeypatch) -> None:
    calls: list[str] = []

    def fake_app(prog_name: str) -> None:
        calls.append(prog_name)

    monkeypatch.setattr("skill_mgr.cli.app", fake_app)
    sys.modules.pop("skill_mgr.main", None)
    runpy.run_module("skill_mgr.main", run_name="__main__")
    assert calls == ["skill-mgr"]
