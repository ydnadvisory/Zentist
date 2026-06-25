from datetime import UTC, datetime
from pathlib import Path

from zentist_rpa.connectors.result_store import SQLiteResultStore
from zentist_rpa.core.models import OutcomeStatus, RunContext, RunStatus, WorkItemOutcome


def test_sqlite_store_upserts_outcomes_by_run_portal_and_item(tmp_path: Path) -> None:
    store = SQLiteResultStore(tmp_path / "results.sqlite3")
    context = RunContext(run_id="run-1", started_at=datetime(2026, 6, 25, tzinfo=UTC))
    store.start_run(context)

    store.record_outcomes(
        context.run_id,
        [
            WorkItemOutcome(
                portal="orangehrm",
                item_key="employee-1",
                status=OutcomeStatus.FAILURE,
                reason="First attempt failed",
                attempts=1,
            ),
        ],
    )
    store.record_outcomes(
        context.run_id,
        [
            WorkItemOutcome(
                portal="orangehrm",
                item_key="employee-1",
                status=OutcomeStatus.SUCCESS,
                reason=None,
                attempts=2,
                output_refs={"attachment": "salary-details.txt"},
            ),
        ],
    )
    store.finish_run(context.run_id, RunStatus.COMPLETED)

    outcomes = store.fetch_outcomes(context.run_id)

    assert outcomes == [
        WorkItemOutcome(
            portal="orangehrm",
            item_key="employee-1",
            status=OutcomeStatus.SUCCESS,
            attempts=2,
            output_refs={"attachment": "salary-details.txt"},
        ),
    ]
