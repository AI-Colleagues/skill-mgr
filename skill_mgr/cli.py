"""Command-line interface."""

from __future__ import annotations
import argparse
from typing import Any
from skill_mgr.adapters import bundled_adapter_matrix
from skill_mgr.errors import SkillMgrError
from skill_mgr.render import render_human, render_json
from skill_mgr.services import SkillManagerService


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skill-mgr")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("install", "update"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("ref")
        subparser.add_argument("--target", "-t", action="append", default=[])
        subparser.add_argument("--human", action="store_true")

    uninstall = subparsers.add_parser("uninstall")
    uninstall.add_argument("name")
    uninstall.add_argument("--target", "-t", action="append", default=[])
    uninstall.add_argument("--human", action="store_true")

    validate = subparsers.add_parser("validate")
    validate.add_argument("ref")
    validate.add_argument("--human", action="store_true")

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--target", "-t", action="append", default=[])
    list_parser.add_argument("--human", action="store_true")

    show = subparsers.add_parser("show")
    show.add_argument("name")
    show.add_argument("--target", "-t", action="append", default=[])
    show.add_argument("--human", action="store_true")

    matrix = subparsers.add_parser("support-matrix")
    matrix.add_argument("--human", action="store_true")

    return parser


def _emit(payload: dict[str, Any], *, human: bool) -> None:
    if human:
        print(render_human(payload))
        return
    print(render_json(payload))


def _dispatch(service: SkillManagerService, args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "install":
        payload = service.install(args.ref, targets=args.target)
    elif args.command == "update":
        payload = service.update(args.ref, targets=args.target)
    elif args.command == "uninstall":
        payload = service.uninstall(args.name, targets=args.target)
    elif args.command == "validate":
        payload = service.validate(args.ref)
    elif args.command == "list":
        payload = service.list(targets=args.target)
    elif args.command == "show":
        payload = service.show(args.name, targets=args.target)
    elif args.command == "support-matrix":
        payload = bundled_adapter_matrix()
    else:
        raise AssertionError(f"Unhandled command {args.command}")
    return payload


def _exit_status(args: argparse.Namespace, payload: dict[str, Any]) -> int:
    if args.command == "validate":
        return 0 if payload["valid"] else 1
    if any(target.get("status") == "error" for target in payload.get("targets", [])):
        return 1
    return 0


def run(argv: list[str] | None = None) -> int:
    """Run the CLI and return an exit status."""
    args = _parser().parse_args(argv)
    service = SkillManagerService()
    try:
        payload = _dispatch(service, args)
        _emit(payload, human=args.human)
        return _exit_status(args, payload)
    except SkillMgrError as exc:
        payload = {"error": {"code": exc.code, "message": str(exc)}}
        _emit(payload, human=getattr(args, "human", False))
        return 1
