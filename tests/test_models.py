from datetime import UTC, datetime

import pytest

from zentist_rpa.core.models import OutcomeStatus, RunContext, WorkItemOutcome


def test_run_context_creates_unique_run_id() -> None:
    context = RunContext.new(portal_filter=("orangehrm",))

    assert context.run_id.startswith("run-")
    assert context.started_at.tzinfo is UTC
    assert context.portal_filter == ("orangehrm",)


def test_outcome_rejects_invalid_attempt_count() -> None:
    with pytest.raises(ValueError, match="attempts"):
        WorkItemOutcome(
            portal="saucedemo",
            item_key="standard_user",
            status=OutcomeStatus.SUCCESS,
            attempts=0,
        )


def test_outcome_rejects_missing_business_keys() -> None:
    with pytest.raises(ValueError, match="portal"):
        WorkItemOutcome(portal=" ", item_key="employee-1", status=OutcomeStatus.FAILURE)

    with pytest.raises(ValueError, match="item_key"):
        WorkItemOutcome(portal="orangehrm", item_key=" ", status=OutcomeStatus.FAILURE)


def test_run_context_accepts_explicit_values() -> None:
    started_at = datetime(2026, 6, 25, tzinfo=UTC)

    context = RunContext(run_id="run-fixed", started_at=started_at)

    assert context.started_at == started_at
