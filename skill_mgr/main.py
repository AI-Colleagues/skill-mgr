"""CLI entry point."""

from __future__ import annotations
import sys
from skill_mgr.cli import run


def main() -> None:
    """Run the CLI and exit with its status."""
    raise SystemExit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
