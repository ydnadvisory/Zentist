from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from zentist_rpa.core.models import OutcomeStatus, WorkItemOutcome

if TYPE_CHECKING:
    from collections.abc import Sequence


def render_summary_report(outcomes: Sequence[WorkItemOutcome]) -> str:
    totals = Counter(outcome.status for outcome in outcomes)
    lines = [
        "Zentist RPA run summary",
        "",
        f"Total items: {len(outcomes)}",
        f"Success: {totals[OutcomeStatus.SUCCESS]}",
        f"Failure: {totals[OutcomeStatus.FAILURE]}",
        f"Skipped: {totals[OutcomeStatus.SKIPPED]}",
    ]

    failures = [outcome for outcome in outcomes if outcome.status != OutcomeStatus.SUCCESS]
    if failures:
        lines.extend(["", "Items needing review:"])
        lines.extend(
            f"- {outcome.portal}:{outcome.item_key} "
            f"{outcome.status.value}"
            f"{f' - {outcome.reason}' if outcome.reason else ''}"
            for outcome in failures
        )

    return "\n".join(lines)
