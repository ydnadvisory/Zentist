import json
import sqlite3
from argparse import Namespace
from pathlib import Path

import pytest

from zentist_rpa import cli
from zentist_rpa.cli import main
from zentist_rpa.core.models import OutcomeStatus, RunContext, WorkItemOutcome

CONFIG_ERROR_EXIT = 2


def test_check_config_validates_environment(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ZENTIST_RPA_REPORT_RECIPIENT", "ops@example.com")

    assert main(["check-config"]) == 0

    assert "Configuration valid" in capsys.readouterr().out


def test_structure_command_prints_boundaries(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["structure"]) == 0

    output = capsys.readouterr().out
    assert "core: runner contracts" in output
    assert "portals/orangehrm" in output
    assert "portals/saucedemo" in output


def test_no_command_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0

    assert "Run and validate the Zentist RPA automation foundation." in capsys.readouterr().out


def test_load_employee_records_accepts_valid_json(tmp_path: Path) -> None:
    employee_path = tmp_path / "employees.json"
    employee_path.write_text(
        json.dumps(
            [
                {
                    "employee_key": "emp001",
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "job_title": "Account Assistant",
                    "employment_status": "Full-Time Permanent",
                    "annual_salary": "90000",
                }
            ]
        ),
        encoding="utf-8",
    )

    assert cli._load_employee_records(employee_path) == [  # noqa: SLF001
        {
            "employee_key": "emp001",
            "first_name": "Jane",
            "last_name": "Smith",
            "job_title": "Account Assistant",
            "employment_status": "Full-Time Permanent",
            "annual_salary": "90000",
        }
    ]


def test_run_rejects_missing_orangehrm_settings(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ZENTIST_RPA_REPORT_RECIPIENT", "ops@example.com")
    monkeypatch.delenv("ZENTIST_RPA_ORANGEHRM_USERNAME_SECRET", raising=False)
    monkeypatch.delenv("ZENTIST_RPA_ORANGEHRM_PASSWORD_SECRET", raising=False)

    with pytest.raises(SystemExit) as exc:
        main(["run"])

    assert exc.value.code == CONFIG_ERROR_EXIT
    assert "Missing required OrangeHRM configuration" in capsys.readouterr().err


def test_run_persists_outcomes_and_sends_report(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "results.sqlite3"
    report_dir = tmp_path / "reports"
    email_dir = tmp_path / "email"

    monkeypatch.setenv("ZENTIST_RPA_REPORT_RECIPIENT", "ops@example.com")
    monkeypatch.setenv("ZENTIST_RPA_ORANGEHRM_USERNAME_SECRET", "orangehrm-username-ref")
    monkeypatch.setenv("ZENTIST_RPA_ORANGEHRM_PASSWORD_SECRET", "orangehrm-password-ref")
    monkeypatch.setenv("ZENTIST_RPA_DATABASE_PATH", str(database_path))
    monkeypatch.setenv("ZENTIST_RPA_REPORT_OUTPUT_DIR", str(report_dir))
    monkeypatch.setenv("ZENTIST_RPA_EMAIL_OUTPUT_DIR", str(email_dir))

    async def fake_run_orangehrm(
        args: Namespace,
        context: RunContext,
    ) -> list[WorkItemOutcome]:
        assert args.portal == "orangehrm"
        assert context.portal_filter == ("orangehrm",)
        return [
            WorkItemOutcome(
                portal="orangehrm",
                item_key="employee-1",
                status=OutcomeStatus.SUCCESS,
                output_refs={"employee_profile_url": "https://example.test/pim/viewEmployee/1"},
            )
        ]

    monkeypatch.setattr(cli, "_run_orangehrm", fake_run_orangehrm)

    assert main(["run"]) == 0

    output = capsys.readouterr().out
    assert "finished with 1 item outcome(s)" in output
    run_id = output.split()[1]

    with sqlite3.connect(database_path) as connection:
        run_status = connection.execute(
            "SELECT status FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        item = connection.execute(
            """
            SELECT portal, item_key, status
            FROM work_item_outcomes
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()

    assert run_status == ("completed",)
    assert item == ("orangehrm", "employee-1", "success")
    assert (
        (report_dir / f"{run_id}-summary.txt")
        .read_text(encoding="utf-8")
        .startswith("Zentist RPA run summary")
    )
    assert (
        (email_dir / f"zentist-rpa-run-{run_id}.txt")
        .read_text(encoding="utf-8")
        .startswith("To: ops@example.com")
    )


def test_run_orangehrm_persists_report_and_email(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    employee_path = tmp_path / "employees.json"
    employee_path.write_text(
        json.dumps(
            [
                {
                    "employee_key": "emp001",
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "job_title": "Account Assistant",
                    "employment_status": "Full-Time Permanent",
                    "annual_salary": "90000",
                }
            ]
        ),
        encoding="utf-8",
    )
    database_path = tmp_path / "db" / "results.sqlite3"
    report_dir = tmp_path / "reports"
    email_dir = tmp_path / "email"
    monkeypatch.setenv("ZENTIST_RPA_REPORT_RECIPIENT", "ops@example.com")
    monkeypatch.setenv("ZENTIST_RPA_ORANGEHRM_USERNAME_SECRET", "orangehrm-username-ref")
    monkeypatch.setenv("ZENTIST_RPA_ORANGEHRM_PASSWORD_SECRET", "orangehrm-password-ref")
    monkeypatch.setenv("ZENTIST_RPA_DATABASE_PATH", str(database_path))
    monkeypatch.setenv("ZENTIST_RPA_REPORT_OUTPUT_DIR", str(report_dir))
    monkeypatch.setenv("ZENTIST_RPA_EMAIL_OUTPUT_DIR", str(email_dir))

    async def fake_run_orangehrm(
        args: Namespace,
        context: RunContext,
    ) -> list[WorkItemOutcome]:
        assert args.employee_json == employee_path
        assert context.portal_filter == ("orangehrm",)
        return [
            WorkItemOutcome(
                portal="orangehrm",
                item_key="emp001",
                status=OutcomeStatus.SUCCESS,
                reason="Employee found; job details saved; salary attachment already existed.",
            )
        ]

    monkeypatch.setattr("zentist_rpa.cli._run_orangehrm", fake_run_orangehrm)

    assert main(["run", "--portal", "orangehrm", "--employee-json", str(employee_path)]) == 0

    output = capsys.readouterr().out
    assert "finished with 1 item outcome" in output
    assert database_path.exists()
    assert len(list(report_dir.glob("*-summary.txt"))) == 1
    assert len(list(email_dir.glob("zentist-rpa-run-*.txt"))) == 1


def test_run_rejects_invalid_employee_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    employee_path = tmp_path / "employees.json"
    employee_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("ZENTIST_RPA_REPORT_RECIPIENT", "ops@example.com")
    monkeypatch.setenv("ZENTIST_RPA_ORANGEHRM_USERNAME_SECRET", "orangehrm-username-ref")
    monkeypatch.setenv("ZENTIST_RPA_ORANGEHRM_PASSWORD_SECRET", "orangehrm-password-ref")
    monkeypatch.setenv("ZENTIST_RPA_DATABASE_PATH", str(tmp_path / "results.sqlite3"))

    with pytest.raises(SystemExit) as exc:
        main(["run", "--employee-json", str(employee_path)])

    assert exc.value.code == CONFIG_ERROR_EXIT


def test_load_employee_records_rejects_invalid_json_shapes(tmp_path: Path) -> None:
    employee_path = tmp_path / "employees.json"

    employee_path.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="not valid JSON"):
        cli._load_employee_records(employee_path)  # noqa: SLF001

    employee_path.write_text(json.dumps(["emp001"]), encoding="utf-8")
    with pytest.raises(TypeError, match="item 0"):
        cli._load_employee_records(employee_path)  # noqa: SLF001

    employee_path.write_text(json.dumps([{"employee_key": 1}]), encoding="utf-8")
    with pytest.raises(TypeError, match="only string keys and values"):
        cli._load_employee_records(employee_path)  # noqa: SLF001


def test_load_employee_records_reports_read_errors(tmp_path: Path) -> None:
    assert cli._load_employee_records(None) is None  # noqa: SLF001
    missing_path = tmp_path / "missing.json"

    with pytest.raises(ValueError, match="Could not read employee JSON"):
        cli._load_employee_records(missing_path)  # noqa: SLF001


def test_run_returns_nonzero_when_portal_reports_failed_outcome(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "results.sqlite3"
    monkeypatch.setenv("ZENTIST_RPA_REPORT_RECIPIENT", "ops@example.com")
    monkeypatch.setenv("ZENTIST_RPA_ORANGEHRM_USERNAME_SECRET", "orangehrm-username-ref")
    monkeypatch.setenv("ZENTIST_RPA_ORANGEHRM_PASSWORD_SECRET", "orangehrm-password-ref")
    monkeypatch.setenv("ZENTIST_RPA_DATABASE_PATH", str(database_path))
    monkeypatch.setenv("ZENTIST_RPA_REPORT_OUTPUT_DIR", str(tmp_path / "reports"))
    monkeypatch.setenv("ZENTIST_RPA_EMAIL_OUTPUT_DIR", str(tmp_path / "email"))

    async def fake_run_orangehrm(
        args: Namespace,
        context: RunContext,
    ) -> list[WorkItemOutcome]:
        del args, context
        return [
            WorkItemOutcome(
                portal="orangehrm",
                item_key="employee-1",
                status=OutcomeStatus.FAILURE,
                reason="Search timed out.",
            )
        ]

    monkeypatch.setattr(cli, "_run_orangehrm", fake_run_orangehrm)

    assert main(["run"]) == 1

    with sqlite3.connect(database_path) as connection:
        run_status = connection.execute("SELECT status FROM runs").fetchone()

    assert run_status == ("failed",)
