from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

from pydantic import ValidationError

from zentist_rpa import __version__
from zentist_rpa.connectors.settings import RuntimeSettings

if TYPE_CHECKING:
    from collections.abc import Sequence

STRUCTURE_TEXT = """core: runner contracts, run context, outcomes, exceptions
connectors: settings, secrets, persistence, reports, email
resilience: bounded retry and timeout policies
portals/orangehrm: OrangeHRM page objects and workflows
portals/saucedemo: Sauce Demo page objects and workflows
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zentist-rpa",
        description="Run and validate the Zentist RPA automation foundation.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subcommands = parser.add_subparsers(dest="command")
    subcommands.add_parser(
        "check-config",
        help="Validate runtime configuration before any browser side effects.",
    )
    subcommands.add_parser("structure", help="Print the configured package boundary map.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "check-config":
        try:
            settings = RuntimeSettings()
        except ValidationError as exc:
            parser.exit(status=2, message=f"Configuration error:\n{exc}\n")
        sys.stdout.write(f"Configuration valid. Database: {settings.database_path}\n")
        return 0

    if args.command == "structure":
        sys.stdout.write(STRUCTURE_TEXT)
        return 0

    parser.print_help()
    return 0
