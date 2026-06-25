from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

    from zentist_rpa.core.models import RunContext, WorkItemOutcome


class PortalRunner(Protocol):
    portal_name: str

    def run(self, context: RunContext) -> Sequence[WorkItemOutcome]: ...
