import pytest

from src.services.retry import retry


def test_retry_returns_after_eventual_success():
    attempts = {"count": 0}

    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("temporary failure")
        return "ok"

    assert retry(flaky, max_attempts=3) == "ok"
    assert attempts["count"] == 3


def test_retry_raises_after_max_attempts():
    attempts = {"count": 0}

    def always_fails():
        attempts["count"] += 1
        raise RuntimeError("still failing")

    with pytest.raises(RuntimeError, match="still failing"):
        retry(always_fails, max_attempts=2)

    assert attempts["count"] == 2


def test_retry_does_not_retry_unlisted_exception_types():
    attempts = {"count": 0}

    def fails_with_value_error():
        attempts["count"] += 1
        raise ValueError("bad input")

    with pytest.raises(ValueError, match="bad input"):
        retry(
            fails_with_value_error,
            max_attempts=3,
            retry_exceptions=(RuntimeError,),
        )

    assert attempts["count"] == 1
