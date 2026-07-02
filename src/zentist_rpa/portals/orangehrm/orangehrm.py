import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from zentist_rpa.core.exceptions import ConfigurationError, PortalAutomationError
from zentist_rpa.core.models import OutcomeStatus, RunContext, WorkItemOutcome
from zentist_rpa.core.runner import PortalRunner
from zentist_rpa.portals.orangehrm.models import EmployeeRecord
from zentist_rpa.portals.orangehrm.utilities import OrangeHRMUtilities
from zentist_rpa.services.playwright_service import PlaywrightService

try:
    from . import PORTAL_NAME
except ImportError:
    PORTAL_NAME = "orangehrm"


EmployeesInput = list[dict[str, str]] | None


@dataclass(frozen=True, slots=True)
class OrangeHRMContext(RunContext): ...


class OrangeHRM(PortalRunner[OrangeHRMContext]):
    _input_records: dict[str, EmployeeRecord]
    _salary_attachment_dir = Path("var/orangehrm/salary-attachments")
    _utilities = OrangeHRMUtilities

    def __init__(
        self,
        playwright_service: PlaywrightService,
        employee_records: EmployeesInput = None,
        portal_name: str = PORTAL_NAME,
    ) -> None:
        self.playwright_service = playwright_service
        self.portal_name = portal_name
        self._input_records = self._build_input_records(employee_records)

    @staticmethod
    def _build_input_records(employee_records: EmployeesInput) -> dict[str, EmployeeRecord]:
        if employee_records is None:
            return {}

        records: dict[str, EmployeeRecord] = {}
        for raw_record in employee_records:
            employee = EmployeeRecord(**raw_record)
            records[employee.employee_key] = employee
        return records

    async def _start_browser(self) -> None:
        await self.playwright_service.start()

    async def _stop_browser(self) -> None:
        await self.playwright_service.stop()

    async def run(self, context: OrangeHRMContext) -> list[WorkItemOutcome]:
        if not context.run_id.strip():
            msg = "run_id is required"
            raise ValueError(msg)

        page = None
        try:
            await self._start_browser()

            page = await self.playwright_service.new_page(is_clear_cookie=True)
            await self._utilities.access_employee_list_page(page)

            # Check if the current page is the login page and perform authentication if necessary
            if await self._utilities.is_login_page(page):
                await self._utilities.authenticate(page)
                await page.wait_for_url(self._utilities.url_employee_list, timeout=10000)
                await self._utilities.access_employee_list_page(page)

            # Process each employee record if available, otherwise return a skipped outcome
            if self._input_records:
                processing_date = datetime.now(tz=UTC).date()
                outcomes = [
                    await self._process_employee(
                        page=page,
                        employee=employee,
                        processing_date=processing_date,
                    )
                    for employee in self._input_records.values()
                ]
            else:
                outcomes = [
                    WorkItemOutcome(
                        portal=self.portal_name,
                        item_key="employee_records",
                        status=OutcomeStatus.SKIPPED,
                        reason="No OrangeHRM employee records configured.",
                    )
                ]
        except PlaywrightTimeoutError as error:
            if page:
                await page.screenshot(path="timeout_debug.png")
            return [
                WorkItemOutcome(
                    portal=self.portal_name,
                    item_key="login_page",
                    status=OutcomeStatus.FAILURE,
                    reason=f"Timeout occurred: {error!s}. Screenshot saved as 'timeout_debug.png'.",
                )
            ]
        except (ConfigurationError, PlaywrightError) as error:
            return [
                WorkItemOutcome(
                    portal=self.portal_name,
                    item_key="login_page",
                    status=OutcomeStatus.FAILURE,
                    reason=f"An error occurred: {error!s}",
                )
            ]
        else:
            return outcomes
        finally:
            await self._stop_browser()

    async def _process_employee(
        self,
        *,
        page: Page,
        employee: EmployeeRecord,
        processing_date: date,
    ) -> WorkItemOutcome:
        try:
            # Process the employee record: find or add the employee,
            # ensure job details and handle salary attachment
            employee_ref = await self._utilities.find_or_add_employee(page, employee)
            await self._utilities.ensure_job_details(page, employee)
            attachment = await self._utilities.ensure_salary_attachment(
                page=page,
                employee=employee,
                processing_date=processing_date,
                attachment_dir=self._salary_attachment_dir,
            )

            employee_action = "created" if employee_ref.was_created else "found"
            attachment_action = "uploaded" if attachment.uploaded else "already existed"
            return WorkItemOutcome(
                portal=self.portal_name,
                item_key=employee.employee_key,
                status=OutcomeStatus.SUCCESS,
                reason=(
                    f"Employee {employee_action}; job details saved; "
                    f"salary attachment {attachment_action}."
                ),
                output_refs={
                    "employee_profile_url": employee_ref.profile_url,
                    "salary_attachment_filename": attachment.filename,
                    "salary_attachment_path": str(attachment.path),
                },
            )
        except PlaywrightTimeoutError as error:
            screenshot_path = Path("var/orangehrm/debug") / f"{employee.employee_key}-timeout.png"
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(screenshot_path))
            return WorkItemOutcome(
                portal=self.portal_name,
                item_key=employee.employee_key,
                status=OutcomeStatus.FAILURE,
                reason=f"Timeout occurred: {error!s}.",
                output_refs={"screenshot": str(screenshot_path)},
            )
        except AssertionError as error:
            return WorkItemOutcome(
                portal=self.portal_name,
                item_key=employee.employee_key,
                status=OutcomeStatus.FAILURE,
                reason=f"Assertion failed: {error!s}",
            )
        except (ConfigurationError, PortalAutomationError, PlaywrightError, OSError) as error:
            return WorkItemOutcome(
                portal=self.portal_name,
                item_key=employee.employee_key,
                status=OutcomeStatus.FAILURE,
                reason=f"An error occurred: {error!s}",
            )


if __name__ == "__main__":
    employee_records = [
        {
            "employee_key": "emp001",
            "first_name": "John",
            "last_name": "Doe",
            "job_title": "Software Engineer",
            "employment_status": "Full-Time Permanent",
            "annual_salary": "80000",
        },
        {
            "employee_key": "emp002",
            "first_name": "Jane",
            "last_name": "Smith",
            "job_title": "Product Manager",
            "employment_status": "Full-Time Permanent",
            "annual_salary": "90000",
        },
    ]

    async def main() -> None:
        playwright_service = PlaywrightService()
        portal = OrangeHRM(playwright_service=playwright_service)
        context = OrangeHRMContext.new()
        outcomes = await portal.run(context)
        for outcome in outcomes:
            print(outcome)  # noqa: T201

    asyncio.run(main())
