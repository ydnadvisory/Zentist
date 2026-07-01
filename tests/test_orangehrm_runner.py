# ruff: noqa: ARG004, ASYNC109, EM101, TRY003

import asyncio
from dataclasses import asdict
from datetime import date
from pathlib import Path

import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from zentist_rpa.core.models import OutcomeStatus
from zentist_rpa.portals.orangehrm.models import EmployeeRecord
from zentist_rpa.portals.orangehrm.orangehrm import OrangeHRM, OrangeHRMContext
from zentist_rpa.portals.orangehrm.utilities import EmployeeRecordRef, SalaryAttachmentResult


class FakePage:
    def __init__(self) -> None:
        self.url = "https://opensource-demo.orangehrmlive.com/web/index.php/pim/viewEmployeeList"
        self.waited_urls: list[str] = []
        self.screenshots: list[str] = []

    async def wait_for_url(self, url: str, *, timeout: int) -> None:
        self.waited_urls.append(f"{url}:{timeout}")

    async def screenshot(self, *, path: str) -> None:
        self.screenshots.append(path)


class FakePlaywrightService:
    def __init__(self) -> None:
        self.page = FakePage()
        self.started = False
        self.stopped = False
        self.clear_cookie_requested = False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def new_page(self, *, is_clear_cookie: bool = False) -> FakePage:
        self.clear_cookie_requested = is_clear_cookie
        return self.page


def _employee_record() -> EmployeeRecord:
    return EmployeeRecord(
        employee_key="emp001",
        first_name="Jane",
        last_name="Smith",
        job_title="Account Assistant",
        employment_status="Full-Time Permanent",
        annual_salary="90000",
    )


def test_orangehrm_indexes_input_records_by_employee_key() -> None:
    runner = OrangeHRM(
        playwright_service=FakePlaywrightService(),
        employee_records=[
            {
                "employee_key": "emp001",
                "first_name": "Jane",
                "last_name": "Smith",
                "job_title": "Account Assistant",
                "employment_status": "Full-Time Permanent",
                "annual_salary": "90000",
            }
        ],
    )

    assert list(runner._input_records) == ["emp001"]  # noqa: SLF001


def test_orangehrm_run_returns_skipped_outcome_without_employee_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    class Utilities:
        @staticmethod
        async def access_employee_list_page(page: FakePage) -> None:
            calls.append("access_employee_list_page")

        @staticmethod
        async def is_login_page(page: FakePage) -> bool:
            calls.append("is_login_page")
            return False

    service = FakePlaywrightService()
    runner = OrangeHRM(playwright_service=service)
    monkeypatch.setattr(runner, "_utilities", Utilities)

    outcomes = asyncio.run(runner.run(OrangeHRMContext.new()))

    assert service.started is True
    assert service.stopped is True
    assert service.clear_cookie_requested is True
    assert calls == ["access_employee_list_page", "is_login_page"]
    assert len(outcomes) == 1
    assert outcomes[0].status is OutcomeStatus.SKIPPED
    assert outcomes[0].item_key == "employee_records"


def test_orangehrm_run_authenticates_and_processes_employee(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    employee = _employee_record()

    class Utilities:
        url_employee_list = "https://example.test/employees"

        @staticmethod
        async def access_employee_list_page(page: FakePage) -> None:
            calls.append("access_employee_list_page")

        @staticmethod
        async def is_login_page(page: FakePage) -> bool:
            calls.append("is_login_page")
            return True

        @staticmethod
        async def authenticate(page: FakePage) -> None:
            calls.append("authenticate")

        @staticmethod
        async def find_or_add_employee(
            page: FakePage,
            employee: EmployeeRecord,
        ) -> EmployeeRecordRef:
            calls.append(f"find_or_add_employee:{employee.employee_key}")
            return EmployeeRecordRef(
                employee_key=employee.employee_key,
                profile_url="https://example.test/profile/emp001",
                was_created=True,
            )

        @staticmethod
        async def ensure_job_details(page: FakePage, employee: EmployeeRecord) -> None:
            calls.append(f"ensure_job_details:{employee.employee_key}")

        @staticmethod
        async def ensure_salary_attachment(
            *,
            page: FakePage,
            employee: EmployeeRecord,
            processing_date: date,
            attachment_dir: Path,
        ) -> SalaryAttachmentResult:
            calls.append(f"ensure_salary_attachment:{employee.employee_key}")
            return SalaryAttachmentResult(
                filename="zentist-salary-emp001.txt",
                path=attachment_dir / "zentist-salary-emp001.txt",
                uploaded=True,
            )

    service = FakePlaywrightService()
    runner = OrangeHRM(playwright_service=service, employee_records=[asdict(employee)])
    monkeypatch.setattr(runner, "_utilities", Utilities)

    outcomes = asyncio.run(runner.run(OrangeHRMContext.new()))

    assert service.page.waited_urls == ["https://example.test/employees:10000"]
    assert calls == [
        "access_employee_list_page",
        "is_login_page",
        "authenticate",
        "access_employee_list_page",
        "find_or_add_employee:emp001",
        "ensure_job_details:emp001",
        "ensure_salary_attachment:emp001",
    ]
    assert len(outcomes) == 1
    assert outcomes[0].status is OutcomeStatus.SUCCESS
    assert outcomes[0].item_key == "emp001"
    assert "Employee created" in str(outcomes[0].reason)
    assert outcomes[0].output_refs["salary_attachment_filename"] == "zentist-salary-emp001.txt"


def test_orangehrm_run_rejects_blank_run_id() -> None:
    runner = OrangeHRM(playwright_service=FakePlaywrightService())
    context = OrangeHRMContext(run_id=" ", started_at=OrangeHRMContext.new().started_at)

    with pytest.raises(ValueError, match="run_id is required"):
        asyncio.run(runner.run(context))


def test_orangehrm_run_returns_failure_for_initial_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Utilities:
        @staticmethod
        async def access_employee_list_page(page: FakePage) -> None:
            raise PlaywrightTimeoutError("employee list did not load")

    service = FakePlaywrightService()
    runner = OrangeHRM(playwright_service=service)
    monkeypatch.setattr(runner, "_utilities", Utilities)

    outcomes = asyncio.run(runner.run(OrangeHRMContext.new()))

    assert service.stopped is True
    assert service.page.screenshots == ["timeout_debug.png"]
    assert len(outcomes) == 1
    assert outcomes[0].status is OutcomeStatus.FAILURE
    assert outcomes[0].item_key == "login_page"
    assert "Timeout occurred" in str(outcomes[0].reason)


def test_orangehrm_process_employee_returns_failure_with_timeout_screenshot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    employee = _employee_record()

    class Utilities:
        @staticmethod
        async def find_or_add_employee(
            page: FakePage,
            employee: EmployeeRecord,
        ) -> EmployeeRecordRef:
            raise PlaywrightTimeoutError("search did not finish")

    service = FakePlaywrightService()
    runner = OrangeHRM(playwright_service=service)
    monkeypatch.setattr(runner, "_utilities", Utilities)
    monkeypatch.chdir(tmp_path)

    outcome = asyncio.run(
        runner._process_employee(  # noqa: SLF001
            page=service.page,
            employee=employee,
            processing_date=date(2026, 7, 1),
        )
    )

    assert outcome.status is OutcomeStatus.FAILURE
    assert outcome.item_key == "emp001"
    assert outcome.output_refs == {"screenshot": "var/orangehrm/debug/emp001-timeout.png"}
    assert service.page.screenshots == ["var/orangehrm/debug/emp001-timeout.png"]
