import pytest

from zentist_rpa.portals.orangehrm.models import EmployeeRecord


def test_employee_record_requires_employee_key() -> None:
    with pytest.raises(ValueError, match="employee_key"):
        EmployeeRecord(
            employee_key=" ",
            first_name="Jane",
            last_name="Smith",
            job_title="Account Assistant",
            employment_status="Full-Time Permanent",
            annual_salary="90000",
        )


def test_employee_record_requires_employee_name() -> None:
    with pytest.raises(ValueError, match="first_name and last_name"):
        EmployeeRecord(
            employee_key="emp001",
            first_name="Jane",
            last_name=" ",
            job_title="Account Assistant",
            employment_status="Full-Time Permanent",
            annual_salary="90000",
        )
