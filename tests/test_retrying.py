import pytest

from zentist_rpa.resilience.retrying import RetryPolicy, run_with_retry


class RetryableTestError(RuntimeError):
    pass


def test_retry_policy_retries_specific_exceptions() -> None:
    expected_attempts = 2
    attempts = 0

    def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RetryableTestError
        return "ok"

    result = run_with_retry(
        operation,
        retry_exceptions=(RetryableTestError,),
        policy=RetryPolicy(
            attempts=expected_attempts,
            min_wait_seconds=0,
            max_wait_seconds=0,
        ),
    )

    assert result == "ok"
    assert attempts == expected_attempts


def test_retry_policy_rejects_invalid_attempt_count() -> None:
    with pytest.raises(ValueError, match="attempts"):
        RetryPolicy(attempts=0)
