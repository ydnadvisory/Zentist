import re
from collections.abc import Awaitable
from contextlib import suppress
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TypeVar

from playwright.async_api import Locator, Page, expect
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from zentist_rpa.connectors.secrets import OrangeHRMSecrets
from zentist_rpa.core.exceptions import PortalAutomationError
from zentist_rpa.portals.orangehrm.models import EmployeeRecord

T = TypeVar("T")


async def _with_element_context(description: str, action: Awaitable[T]) -> T:
    try:
        return await action
    except PlaywrightTimeoutError as error:
        message = f"Timed out while {description}: {error.message}"
        raise PlaywrightTimeoutError(message) from error


@dataclass(frozen=True, slots=True)
class EmployeeRecordRef:
    employee_key: str
    profile_url: str
    was_created: bool


@dataclass(frozen=True, slots=True)
class SalaryAttachmentResult:
    filename: str
    path: Path
    uploaded: bool


class OrangeHRMUtilities:
    _url_base = "https://opensource-demo.orangehrmlive.com"
    _login_path = "/web/index.php/auth/login"
    _employee_list_path = "/web/index.php/pim/viewEmployeeList"
    _add_employee_path = "/web/index.php/pim/addEmployee"
    _employee_edit_path = "/web/index.php/pim/viewPersonalDetails/"
    _employee_job_path = "/web/index.php/pim/viewJobDetails/"
    _employee_salary_path = "/web/index.php/pim/viewSalaryList/"
    _employee_row_selector = ".oxd-table-card"
    _employee_edit_button_selector = ".oxd-table-cell-actions button:has(i.bi-pencil-fill)"

    url_login = f"{_url_base}{_login_path}"
    url_employee_list = f"{_url_base}{_employee_list_path}"
    url_add_employee = f"{_url_base}{_add_employee_path}"

    @staticmethod
    def salary_attachment_filename(employee: EmployeeRecord, processing_date: date) -> str:
        return f"zentist-salary-{employee.employee_key}-{processing_date.isoformat()}.txt"

    @staticmethod
    def salary_attachment_text(employee: EmployeeRecord, processing_date: date) -> str:
        return "\n".join(
            (
                "Zentist salary details",
                f"Employee Key: {employee.employee_key}",
                f"Employee Name: {employee.first_name} {employee.last_name}",
                f"Job Title: {employee.job_title}",
                f"Employment Status: {employee.employment_status}",
                f"Annual Salary: {employee.currency} {employee.annual_salary}",
                f"Processing Date: {processing_date.isoformat()}",
                "",
            )
        )

    @staticmethod
    def _exact_text(value: str) -> re.Pattern[str]:
        return re.compile(rf"^{re.escape(value)}$")

    @staticmethod
    def _field_group(container: Page | Locator, label: str) -> Locator:
        exact_label = OrangeHRMUtilities._exact_text(label)
        return (
            container.locator(".oxd-input-group")
            .filter(has=container.locator("label.oxd-label", has_text=exact_label))
            .first
        )

    @staticmethod
    async def _fill_text_field(container: Page | Locator, label: str, value: str) -> None:
        await _with_element_context(
            f"filling '{label}' field",
            OrangeHRMUtilities._field_group(container, label).locator("input").fill(value),
        )

    @staticmethod
    async def _choose_oxd_select(container: Page | Locator, label: str, option: str) -> None:
        group = OrangeHRMUtilities._field_group(container, label)
        await _with_element_context(
            f"clicking '{label}' select field",
            group.locator(".oxd-select-text").click(),
        )

        dropdown = group.locator(".oxd-select-dropdown")
        await _with_element_context(
            f"waiting for '{label}' dropdown to become visible",
            expect(dropdown).to_be_visible(timeout=10000),
        )

        option_locator = dropdown.locator(
            ".oxd-select-option",
            has_text=OrangeHRMUtilities._exact_text(option),
        ).first
        await _with_element_context(
            f"waiting for option '{option}' to appear for '{label}'",
            expect(option_locator).to_be_visible(timeout=30000),
        )
        await _with_element_context(
            f"selecting option '{option}' for '{label}'",
            option_locator.click(force=True),
        )

        if await dropdown.is_visible():
            await group.page.keyboard.press("Escape")
            await _with_element_context(
                f"waiting for '{label}' dropdown to close",
                expect(dropdown).to_be_hidden(timeout=10000),
            )

    @staticmethod
    async def _wait_for_page_idle(page: Page) -> None:
        loaders = page.locator(".oxd-table-loader")
        if await loaders.count() > 0:
            await _with_element_context(
                "waiting for OrangeHRM table loader",
                expect(loaders.first).to_be_hidden(timeout=30000),
            )

    @staticmethod
    async def _wait_for_search_results(page: Page, employee_key: str) -> None:
        loader = page.locator(".oxd-table-loader").first
        with suppress(PlaywrightTimeoutError):
            await expect(loader).to_be_visible(timeout=1000)
        await OrangeHRMUtilities._wait_for_page_idle(page)
        await _with_element_context(
            f"waiting for Employee List search results for '{employee_key}'",
            page.wait_for_function(
                """employeeKey => {
                    const bodyText = document.body.innerText;
                    if (bodyText.includes('No Records Found')) {
                        return true;
                    }
                    return Array.from(document.querySelectorAll('.oxd-table-card'))
                        .some((row) => row.innerText.includes(employeeKey));
                }""",
                arg=employee_key,
                timeout=30000,
            ),
        )

    @staticmethod
    async def access_employee_list_page(page: Page) -> None:
        await _with_element_context(
            f"navigating to '{OrangeHRMUtilities.url_employee_list}'",
            page.goto(OrangeHRMUtilities.url_employee_list, wait_until="domcontentloaded"),
        )
        if await OrangeHRMUtilities.is_login_page(page):
            return
        await _with_element_context(
            "waiting for Employee List search form",
            expect(page.get_by_role("heading", name="Employee Information")).to_be_visible(
                timeout=30000
            ),
        )
        await OrangeHRMUtilities._wait_for_page_idle(page)

    @staticmethod
    async def go_to_employee_list_page(page: Page) -> None:
        await OrangeHRMUtilities.access_employee_list_page(page)

    @staticmethod
    async def find_employee(page: Page, employee: EmployeeRecord) -> EmployeeRecordRef | None:
        await OrangeHRMUtilities.access_employee_list_page(page)
        await OrangeHRMUtilities._fill_text_field(page, "Employee Id", employee.employee_key)
        await _with_element_context(
            f"searching for employee '{employee.employee_key}'",
            page.locator(".oxd-form-actions button[type='submit']").click(),
        )
        await OrangeHRMUtilities._wait_for_search_results(page, employee.employee_key)

        rows = page.locator(OrangeHRMUtilities._employee_row_selector)
        row_count = await _with_element_context(
            f"counting Employee List rows for '{employee.employee_key}'",
            rows.count(),
        )
        if row_count == 0:
            return None
        if row_count > 1:
            msg = f"Employee Id '{employee.employee_key}' matched {row_count} rows"
            raise PortalAutomationError(
                portal="orangehrm",
                operation="find_employee",
                reason=msg,
            )

        await OrangeHRMUtilities._open_employee_row(rows.first)
        return EmployeeRecordRef(
            employee_key=employee.employee_key,
            profile_url=page.url,
            was_created=False,
        )

    @staticmethod
    async def _open_employee_row(row: Locator) -> None:
        await _with_element_context(
            "clicking employee row edit button",
            row.locator(OrangeHRMUtilities._employee_edit_button_selector).click(),
        )
        await _with_element_context(
            "waiting for employee personal details page",
            row.page.wait_for_url(f"**{OrangeHRMUtilities._employee_edit_path}**", timeout=30000),
        )

    @staticmethod
    async def add_employee(page: Page, employee: EmployeeRecord) -> EmployeeRecordRef:
        await _with_element_context(
            "opening Add Employee page",
            page.get_by_role("link", name="Add Employee").click(),
        )
        await _with_element_context(
            "waiting for Add Employee page",
            page.wait_for_url(f"**{OrangeHRMUtilities._add_employee_path}", timeout=30000),
        )
        await _with_element_context(
            "waiting for Add Employee form",
            expect(page.get_by_role("heading", name="Add Employee")).to_be_visible(timeout=30000),
        )
        await _with_element_context(
            "filling employee first name",
            page.locator('input[name="firstName"]').fill(employee.first_name),
        )
        await _with_element_context(
            "filling employee last name",
            page.locator('input[name="lastName"]').fill(employee.last_name),
        )
        await OrangeHRMUtilities._fill_add_employee_id(page, employee.employee_key)
        await _with_element_context(
            f"saving employee '{employee.employee_key}'",
            page.get_by_role("button", name="Save").click(),
        )
        await _with_element_context(
            "waiting for created employee personal details page",
            page.wait_for_url(f"**{OrangeHRMUtilities._employee_edit_path}**", timeout=30000),
        )
        return EmployeeRecordRef(
            employee_key=employee.employee_key,
            profile_url=page.url,
            was_created=True,
        )

    @staticmethod
    async def _fill_add_employee_id(page: Page, employee_key: str) -> None:
        add_form = page.locator(".orangehrm-employee-form").first
        labeled_employee_id = OrangeHRMUtilities._field_group(add_form, "Employee Id")
        if await labeled_employee_id.count() > 0:
            await _with_element_context(
                "filling Add Employee 'Employee Id' field",
                labeled_employee_id.locator("input").fill(employee_key),
            )
            return

        await _with_element_context(
            "filling Add Employee id field",
            add_form.locator(".oxd-input-group input.oxd-input").last.fill(employee_key),
        )

    @staticmethod
    async def find_or_add_employee(page: Page, employee: EmployeeRecord) -> EmployeeRecordRef:
        existing_employee = await OrangeHRMUtilities.find_employee(page, employee)
        if existing_employee is not None:
            return existing_employee
        return await OrangeHRMUtilities.add_employee(page, employee)

    @staticmethod
    async def ensure_job_details(page: Page, employee: EmployeeRecord) -> None:
        await OrangeHRMUtilities._open_employee_tab(
            page=page,
            tab_name="Job",
            expected_path=OrangeHRMUtilities._employee_job_path,
        )
        await OrangeHRMUtilities._choose_oxd_select(page, "Job Title", employee.job_title)
        await OrangeHRMUtilities._choose_oxd_select(
            page,
            "Employment Status",
            employee.employment_status,
        )
        await _with_element_context(
            f"saving Job details for employee '{employee.employee_key}'",
            page.get_by_role("button", name="Save").click(),
        )
        await OrangeHRMUtilities._wait_for_page_idle(page)

    @staticmethod
    async def ensure_salary_attachment(
        page: Page,
        employee: EmployeeRecord,
        processing_date: date,
        attachment_dir: Path,
    ) -> SalaryAttachmentResult:
        await OrangeHRMUtilities._open_employee_tab(
            page=page,
            tab_name="Salary",
            expected_path=OrangeHRMUtilities._employee_salary_path,
        )
        filename = OrangeHRMUtilities.salary_attachment_filename(employee, processing_date)
        attachment_path = OrangeHRMUtilities._salary_attachment_path(
            employee=employee,
            processing_date=processing_date,
            attachment_dir=attachment_dir,
        )
        local_marker_exists = attachment_path.exists()

        attachment_section = page.locator(".orangehrm-attachment").first
        await _with_element_context(
            "waiting for Salary attachments section",
            expect(attachment_section).to_be_visible(timeout=30000),
        )
        await OrangeHRMUtilities._wait_for_page_idle(page)
        if await OrangeHRMUtilities._attachment_exists(attachment_section, filename):
            return SalaryAttachmentResult(
                filename=filename,
                path=attachment_path,
                uploaded=False,
            )

        if local_marker_exists:
            msg = (
                f"Local salary attachment marker '{filename}' already exists, but OrangeHRM "
                "does not expose a matching attachment row; manual review required to avoid "
                "a duplicate upload."
            )
            raise PortalAutomationError(
                portal="orangehrm",
                operation="ensure_salary_attachment",
                reason=msg,
            )

        OrangeHRMUtilities._write_salary_attachment(
            employee=employee,
            processing_date=processing_date,
            attachment_dir=attachment_dir,
        )
        await _with_element_context(
            "opening Add Attachment form",
            attachment_section.locator(".orangehrm-action-header button", has_text="Add").click(),
        )
        await _with_element_context(
            "attaching salary details file",
            attachment_section.locator('input[type="file"]').set_input_files(attachment_path),
        )
        await _with_element_context(
            "filling salary attachment comment",
            attachment_section.locator("textarea").fill(
                f"Zentist salary attachment marker: {filename}"
            ),
        )
        await _with_element_context(
            "saving salary attachment",
            attachment_section.get_by_role("button", name="Save").click(),
        )
        await _with_element_context(
            "waiting for Add Attachment form to close",
            expect(attachment_section.get_by_role("heading", name="Add Attachment")).to_be_hidden(
                timeout=30000
            ),
        )
        await OrangeHRMUtilities._wait_for_page_idle(page)
        if not await OrangeHRMUtilities._attachment_exists(attachment_section, filename):
            msg = f"OrangeHRM did not expose uploaded salary attachment '{filename}' after save"
            raise PortalAutomationError(
                portal="orangehrm",
                operation="ensure_salary_attachment",
                reason=msg,
            )
        return SalaryAttachmentResult(
            filename=filename,
            path=attachment_path,
            uploaded=True,
        )

    @staticmethod
    async def _open_employee_tab(page: Page, tab_name: str, expected_path: str) -> None:
        await _with_element_context(
            f"opening employee '{tab_name}' tab",
            page.locator(
                "a.orangehrm-tabs-item", has_text=OrangeHRMUtilities._exact_text(tab_name)
            ).first.click(),
        )
        await _with_element_context(
            f"waiting for employee '{tab_name}' tab",
            page.wait_for_url(f"**{expected_path}**", timeout=30000),
        )

    @staticmethod
    def _salary_attachment_path(
        employee: EmployeeRecord,
        processing_date: date,
        attachment_dir: Path,
    ) -> Path:
        return attachment_dir / OrangeHRMUtilities.salary_attachment_filename(
            employee,
            processing_date,
        )

    @staticmethod
    def _write_salary_attachment(
        employee: EmployeeRecord,
        processing_date: date,
        attachment_dir: Path,
    ) -> Path:
        attachment_dir.mkdir(parents=True, exist_ok=True)
        attachment_path = OrangeHRMUtilities._salary_attachment_path(
            employee=employee,
            processing_date=processing_date,
            attachment_dir=attachment_dir,
        )
        attachment_path.write_text(
            OrangeHRMUtilities.salary_attachment_text(employee, processing_date),
            encoding="utf-8",
        )
        return attachment_path

    @staticmethod
    async def _attachment_exists(attachment_section: Locator, filename: str) -> bool:
        rows = attachment_section.locator(OrangeHRMUtilities._employee_row_selector)
        row_count = await rows.count()
        for index in range(row_count):
            if filename in await rows.nth(index).inner_text():
                return True
        return False

    @staticmethod
    async def is_login_page(page: Page) -> bool:
        return OrangeHRMUtilities._login_path in page.url

    @staticmethod
    async def authenticate(page: Page) -> None:
        secrets = OrangeHRMSecrets()
        await _with_element_context(
            "filling username field",
            page.fill('input[name="username"]', secrets.get_secret("username")),
        )
        await _with_element_context(
            "filling password field",
            page.fill('input[name="password"]', secrets.get_secret("password")),
        )
        await _with_element_context("clicking submit button", page.click('button[type="submit"]'))
