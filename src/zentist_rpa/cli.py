from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

from zentist_rpa import __version__
from zentist_rpa.connectors.email import EmailMessage, FileEmailSender
from zentist_rpa.connectors.reporting import render_summary_report
from zentist_rpa.connectors.result_store import SQLiteResultStore
from zentist_rpa.connectors.settings import RuntimeSettings
from zentist_rpa.core.models import OutcomeStatus, RunContext, RunStatus, WorkItemOutcome
from zentist_rpa.portals.orangehrm.orangehrm import EmployeesInput, OrangeHRM, OrangeHRMContext
from zentist_rpa.services.playwright_service import PlaywrightService

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
    run_parser = subcommands.add_parser("run", help="Run a configured portal automation.")
    run_parser.add_argument(
        "--portal",
        choices=("orangehrm",),
        default="orangehrm",
        help="Portal automation to run.",
    )
    run_parser.add_argument(
        "--employee-json",
        type=Path,
        help="Path to a JSON array of OrangeHRM employee records.",
    )
    run_parser.add_argument(
        "--headed",
        action="store_true",
        help="Run the browser headed instead of headless.",
    )
    return parser


def _load_employee_records(path: Path | None) -> EmployeesInput:
    if path is None:
        return None

    try:
        raw_records = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        msg = f"Could not read employee JSON '{path}': {exc}"
        raise ValueError(msg) from exc
    except json.JSONDecodeError as exc:
        msg = f"Employee JSON '{path}' is not valid JSON: {exc}"
        raise ValueError(msg) from exc

    if not isinstance(raw_records, list):
        msg = "Employee JSON must be a list of objects"
        raise TypeError(msg)

    records: list[dict[str, str]] = []
    for index, raw_record in enumerate(raw_records):
        if not isinstance(raw_record, dict):
            msg = f"Employee JSON item {index} must be an object"
            raise TypeError(msg)

        record: dict[str, str] = {}
        for key, value in raw_record.items():
            if not isinstance(key, str) or not isinstance(value, str):
                msg = f"Employee JSON item {index} must contain only string keys and values"
                raise TypeError(msg)
            record[key] = value
        records.append(record)
    return records


def _write_report(
    context: RunContext,
    settings: RuntimeSettings,
    outcomes: Sequence[WorkItemOutcome],
) -> Path:
    report = render_summary_report(outcomes)
    settings.report_output_dir.mkdir(parents=True, exist_ok=True)
    report_path = settings.report_output_dir / f"{context.run_id}-summary.txt"
    report_path.write_text(report, encoding="utf-8")

    sender = FileEmailSender(settings.email_output_dir)
    if settings.report_recipient is None:
        msg = "report_recipient is required"
        raise RuntimeError(msg)
    sender.send(
        EmailMessage(
            recipient=settings.report_recipient,
            subject=f"Zentist RPA Run {context.run_id}",
            body=report,
        )
    )
    return report_path


async def _run_orangehrm(
    args: argparse.Namespace,
    context: OrangeHRMContext,
) -> list[WorkItemOutcome]:
    employee_records = _load_employee_records(args.employee_json)
    runner = OrangeHRM(
        playwright_service=PlaywrightService(headless=not args.headed),
        employee_records=employee_records,
    )
    return list(await runner.run(context))


def _has_failed_outcome(outcomes: Sequence[WorkItemOutcome]) -> bool:
    return any(outcome.status == OutcomeStatus.FAILURE for outcome in outcomes)


def _require_orangehrm_settings(settings: RuntimeSettings) -> None:
    missing = [
        name
        for name, value in (
            ("ZENTIST_RPA_ORANGEHRM_USERNAME_SECRET", settings.orangehrm_username_secret),
            ("ZENTIST_RPA_ORANGEHRM_PASSWORD_SECRET", settings.orangehrm_password_secret),
        )
        if not value
    ]
    if missing:
        msg = f"Missing required OrangeHRM configuration: {', '.join(missing)}"
        raise ValueError(msg)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        settings = RuntimeSettings() if args.command in {"check-config", "run"} else None
    except ValidationError as exc:
        parser.exit(status=2, message=f"Configuration error:\n{exc}\n")

    if args.command == "check-config":
        if settings is None:
            msg = "settings were not loaded"
            raise RuntimeError(msg)
        sys.stdout.write(f"Configuration valid. Database: {settings.database_path}\n")
        return 0

    if args.command == "run":
        if settings is None:
            msg = "settings were not loaded"
            raise RuntimeError(msg)

        try:
            _require_orangehrm_settings(settings)
        except ValueError as exc:
            parser.exit(status=2, message=f"Configuration error: {exc}\n")

        try:
            context = OrangeHRMContext.new(portal_filter=(args.portal,))
            store = SQLiteResultStore(settings.database_path)
            store.start_run(context)
            outcomes = asyncio.run(_run_orangehrm(args, context))
            store.record_outcomes(context.run_id, outcomes)
            store.finish_run(
                context.run_id,
                RunStatus.FAILED if _has_failed_outcome(outcomes) else RunStatus.COMPLETED,
            )
            report_path = _write_report(context, settings, outcomes)
        except (TypeError, ValueError) as exc:
            parser.exit(status=2, message=f"Input error: {exc}\n")

        sys.stdout.write(
            f"Run {context.run_id} finished with {len(outcomes)} item outcome(s).\n"
            f"Report: {report_path}\n"
        )
        return 1 if _has_failed_outcome(outcomes) else 0

    if args.command == "structure":
        sys.stdout.write(STRUCTURE_TEXT)
        return 0

    parser.print_help()
    return 0
