from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar

from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

if TYPE_CHECKING:
    from collections.abc import Callable


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    attempts: int = 3
    min_wait_seconds: float = 1
    max_wait_seconds: float = 10

    def __post_init__(self) -> None:
        if self.attempts < 1:
            msg = "attempts must be at least 1"
            raise ValueError(msg)


def run_with_retry(
    operation: Callable[[], T],
    *,
    retry_exceptions: tuple[type[BaseException], ...],
    policy: RetryPolicy,
) -> T:
    retrying = Retrying(
        retry=retry_if_exception_type(retry_exceptions),
        stop=stop_after_attempt(policy.attempts),
        wait=wait_exponential(min=policy.min_wait_seconds, max=policy.max_wait_seconds),
        reraise=True,
    )
    return retrying(operation)
