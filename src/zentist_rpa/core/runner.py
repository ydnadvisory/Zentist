from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypeVar

if TYPE_CHECKING:
    from collections.abc import Sequence

    from zentist_rpa.core.models import RunContext, WorkItemOutcome
    from zentist_rpa.services.playwright_service import PlaywrightService

RunContextT_contra = TypeVar("RunContextT_contra", bound="RunContext", contravariant=True)


class PortalRunner(Protocol[RunContextT_contra]):
    portal_name: str
    playwright_service: PlaywrightService

    async def run(self, context: RunContextT_contra) -> Sequence[WorkItemOutcome]: ...
