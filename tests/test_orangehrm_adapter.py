from __future__ import annotations

# ruff: noqa: SLF001
import argparse
import asyncio

import pytest

from zentist_rpa.core.models import OutcomeStatus, RunContext, WorkItemOutcome
from zentist_rpa.portals.orangehrm import adapter


def test_run_orangehrm_builds_runner_context_and_launches_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: dict[str, object] = {}

    class FakePlaywrightService:
        def __init__(self, *, headless: bool) -> None:
            recorded["headless"] = headless

    class FakeRunner:
        def __init__(self, *, playwright_service: object, employee_records: object) -> None:
            recorded["playwright_service"] = playwright_service
            recorded["employee_records"] = employee_records

        async def run(self, context: RunContext) -> list[WorkItemOutcome]:
            recorded["context"] = context
            return [
                WorkItemOutcome(
                    portal="orangehrm",
                    item_key="employee-1",
                    status=OutcomeStatus.SUCCESS,
                ),
            ]

    monkeypatch.setattr(adapter, "PlaywrightService", FakePlaywrightService)
    monkeypatch.setattr(adapter, "OrangeHRM", FakeRunner)

    args = argparse.Namespace(employee_json=None, headed=False)
    base_context = RunContext.new(portal_filter=("orangehrm",))

    outcomes = asyncio.run(adapter._run_orangehrm(args, base_context, object()))

    assert outcomes == [
        WorkItemOutcome(
            portal="orangehrm",
            item_key="employee-1",
            status=OutcomeStatus.SUCCESS,
        ),
    ]
    assert recorded["headless"] is True
    assert recorded["context"] is not None


def test_load_employee_records_rejects_non_list_payload(tmp_path: object) -> None:
    json_file = tmp_path / "employees.json"
    json_file.write_text("""{"employee_key": "emp001"}""", encoding="utf-8")

    with pytest.raises(TypeError, match="must be a list of objects"):
        adapter._load_employee_records(json_file)


def test_load_employee_records_rejects_invalid_record_shape(tmp_path: object) -> None:
    json_file = tmp_path / "employees.json"
    json_file.write_text("[1]", encoding="utf-8")

    with pytest.raises(TypeError, match="must be an object"):
        adapter._load_employee_records(json_file)
