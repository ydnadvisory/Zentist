import asyncio
from datetime import date
from pathlib import Path

import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from zentist_rpa.portals.orangehrm.models import EmployeeRecord
from zentist_rpa.portals.orangehrm.utilities import OrangeHRMUtilities, _with_element_context


def test_salary_attachment_filename_includes_employee_key_and_processing_date() -> None:
    employee = EmployeeRecord(
        employee_key="emp001",
        first_name="Jane",
        last_name="Smith",
        job_title="Account Assistant",
        employment_status="Full-Time Permanent",
        annual_salary="90000",
    )

    filename = OrangeHRMUtilities.salary_attachment_filename(employee, date(2026, 7, 1))

    assert filename == "zentist-salary-emp001-2026-07-01.txt"


def test_salary_attachment_text_contains_target_employee_details() -> None:
    employee = EmployeeRecord(
        employee_key="emp001",
        first_name="Jane",
        last_name="Smith",
        job_title="Account Assistant",
        employment_status="Full-Time Permanent",
        annual_salary="90000",
    )

    text = OrangeHRMUtilities.salary_attachment_text(employee, date(2026, 7, 1))

    assert "Employee Key: emp001" in text
    assert "Employee Name: Jane Smith" in text
    assert "Job Title: Account Assistant" in text
    assert "Employment Status: Full-Time Permanent" in text
    assert "Annual Salary: USD 90000" in text
    assert "Processing Date: 2026-07-01" in text


def test_choose_select_option_finds_by_normalized_case_and_spacing() -> None:
    resolved = OrangeHRMUtilities._resolve_select_option(  # noqa: SLF001
        "Employment Status",
        "  contract  ",
        ["-- Select --", "Freelance", "Full-Time Contract", "Full-Time Permanent", "Part-Time Internship"],
    )

    assert resolved == "Full-Time Contract"


def test_choose_select_option_prefers_exact_match() -> None:
    resolved = OrangeHRMUtilities._resolve_select_option(  # noqa: SLF001
        "Job Title",
        "Software Engineer",
        ["Software Architect", "Software Engineer", "Software QA"],
    )

    assert resolved == "Software Engineer"


def test_choose_select_option_raises_when_unmatched() -> None:
    with pytest.raises(
        AssertionError,
        match="Could not resolve 'Software Intern' for 'Job Title' from dropdown options",
    ):
        OrangeHRMUtilities._resolve_select_option(  # noqa: SLF001
            "Job Title",
            "Software Intern",
            ["Software Architect", "Quality Specialist"],
        )


def test_salary_attachment_write_creates_deterministic_file(tmp_path: Path) -> None:
    employee = EmployeeRecord(
        employee_key="emp001",
        first_name="Jane",
        last_name="Smith",
        job_title="Account Assistant",
        employment_status="Full-Time Permanent",
        annual_salary="90000",
    )

    path = OrangeHRMUtilities._write_salary_attachment(  # noqa: SLF001
        employee=employee,
        processing_date=date(2026, 7, 1),
        attachment_dir=tmp_path,
    )

    assert path == tmp_path / "zentist-salary-emp001-2026-07-01.txt"
    assert path.read_text(encoding="utf-8").startswith("Zentist salary details\n")


def test_exact_text_escapes_user_supplied_value() -> None:
    pattern = OrangeHRMUtilities._exact_text("A+B (C)")  # noqa: SLF001

    assert pattern.match("A+B (C)")
    assert not pattern.match("AAB (C)")


def test_with_element_context_returns_successful_result() -> None:
    async def action() -> str:
        return "ok"

    result = asyncio.run(_with_element_context("checking field", action()))

    assert result == "ok"


def test_with_element_context_adds_actionable_timeout_context() -> None:
    async def action() -> str:
        message = "raw timeout"
        raise PlaywrightTimeoutError(message)

    with pytest.raises(PlaywrightTimeoutError, match="Timed out while checking field"):
        asyncio.run(_with_element_context("checking field", action()))


def test_attachment_exists_checks_each_rendered_attachment_row() -> None:
    class FakeRow:
        def __init__(self, text: str) -> None:
            self._text = text

        async def inner_text(self) -> str:
            return self._text

    class FakeRows:
        def __init__(self, rows: list[FakeRow]) -> None:
            self._rows = rows

        async def count(self) -> int:
            return len(self._rows)

        def nth(self, index: int) -> FakeRow:
            return self._rows[index]

    class FakeAttachmentSection:
        def __init__(self, rows: list[FakeRow]) -> None:
            self._rows = FakeRows(rows)

        def locator(self, selector: str) -> FakeRows:
            assert selector == ".oxd-table-card"
            return self._rows

    attachment_section = FakeAttachmentSection(
        [
            FakeRow("other-file.txt"),
            FakeRow("zentist-salary-emp001-2026-07-01.txt"),
        ]
    )

    exists = asyncio.run(
        OrangeHRMUtilities._attachment_exists(  # noqa: SLF001
            attachment_section,
            "zentist-salary-emp001-2026-07-01.txt",
        )
    )

    assert exists is True
