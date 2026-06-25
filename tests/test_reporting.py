from zentist_rpa.connectors.reporting import render_summary_report
from zentist_rpa.core.models import OutcomeStatus, WorkItemOutcome


def test_summary_report_counts_and_lists_non_success_items() -> None:
    report = render_summary_report(
        [
            WorkItemOutcome(
                portal="saucedemo",
                item_key="standard_user",
                status=OutcomeStatus.SUCCESS,
            ),
            WorkItemOutcome(
                portal="saucedemo",
                item_key="locked_out_user",
                status=OutcomeStatus.SKIPPED,
                reason="Account is locked",
            ),
        ],
    )

    assert "Total items: 2" in report
    assert "Success: 1" in report
    assert "Skipped: 1" in report
    assert "saucedemo:locked_out_user skipped - Account is locked" in report
