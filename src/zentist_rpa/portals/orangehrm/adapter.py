from __future__ import annotations

import argparse
import json
from pathlib import Path

from zentist_rpa.connectors.settings import RuntimeSettings
from zentist_rpa.core.models import RunContext, WorkItemOutcome
from zentist_rpa.portals.orangehrm import PORTAL_NAME
from zentist_rpa.portals.orangehrm.orangehrm import EmployeesInput, OrangeHRM, OrangeHRMContext
from zentist_rpa.portals.registry import PortalAdapter
from zentist_rpa.services.playwright_service import PlaywrightService


def _configure_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--employee-json",
        type=Path,
        help="Path to a JSON array of OrangeHRM employee records.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run the browser headed instead of headless.",
    )


def _validate_settings(settings: RuntimeSettings) -> None:
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


def _build_context(_args: argparse.Namespace) -> RunContext:
    return OrangeHRMContext.new(portal_filter=(PORTAL_NAME,))


async def _run_orangehrm(
    args: argparse.Namespace,
    context: OrangeHRMContext,
    settings: RuntimeSettings,
) -> list[WorkItemOutcome]:
    del settings
    employee_records = _load_employee_records(args.employee_json)
    runner = OrangeHRM(
        playwright_service=PlaywrightService(headless=not args.headed),
        employee_records=employee_records,
    )
    return list(await runner.run(context))


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


ORANGEHRM_ADAPTER = PortalAdapter(
    name=PORTAL_NAME,
    configure_parser=_configure_parser,
    validate_settings=_validate_settings,
    build_context=_build_context,
    run=_run_orangehrm,
)
