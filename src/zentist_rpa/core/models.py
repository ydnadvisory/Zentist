from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Self
from uuid import uuid4

if TYPE_CHECKING:
    from collections.abc import Mapping


class OutcomeStatus(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"


class RunStatus(StrEnum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class RunContext:
    run_id: str
    started_at: datetime
    portal_filter: tuple[str, ...] = ()

    @classmethod
    def new(cls, *, portal_filter: tuple[str, ...] = ()) -> Self:
        return cls(
            run_id=f"run-{uuid4().hex}",
            started_at=datetime.now(tz=UTC),
            portal_filter=portal_filter,
        )


@dataclass(frozen=True, slots=True)
class WorkItemOutcome:
    portal: str
    item_key: str
    status: OutcomeStatus
    reason: str | None = None
    attempts: int = 1
    output_refs: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.portal.strip():
            msg = "portal is required"
            raise ValueError(msg)
        if not self.item_key.strip():
            msg = "item_key is required"
            raise ValueError(msg)
        if self.attempts < 1:
            msg = "attempts must be at least 1"
            raise ValueError(msg)
