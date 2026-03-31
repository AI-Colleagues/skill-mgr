"""CLI entry point."""

from __future__ import annotations
from skill_mgr.cli import app


def main() -> None:
    """Run the CLI and exit with its status."""
    app(prog_name="skill-mgr")


if __name__ == "__main__":
    main()
