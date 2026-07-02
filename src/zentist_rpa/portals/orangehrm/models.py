from dataclasses import dataclass
from enum import StrEnum


class RecordChangeStatus(StrEnum):
    NEW = "new"
    UPDATED = "updated"
    UNCHANGED = "unchanged"


@dataclass(frozen=True, slots=True)
class EmployeeRecord:
    employee_key: str
    first_name: str
    last_name: str
    job_title: str
    employment_status: str
    annual_salary: str
    currency: str = "USD"

    def __post_init__(self) -> None:
        if not self.employee_key.strip():
            msg = "employee_key is required"
            raise ValueError(msg)
        if not self.first_name.strip() or not self.last_name.strip():
            msg = "first_name and last_name are required"
            raise ValueError(msg)
